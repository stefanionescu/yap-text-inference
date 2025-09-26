"""Sequential execution: tool-first, then chat streaming."""

import asyncio
import json
import os
import uuid
from typing import Any, Dict
from fastapi import WebSocket

from .tool_runner import run_toolcall
from .tool_parser import parse_tool_result
from .chat_streamer import run_chat_stream
from ..engines import get_tool_engine
from ..handlers.session_manager import session_manager


async def run_sequential_execution(
    ws: WebSocket,
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
) -> None:
    """Execute sequential tool-then-chat workflow.
    
    Args:
        ws: WebSocket connection
        session_id: Session identifier
        static_prefix: Static persona prefix
        runtime_text: Runtime persona text
        history_text: Conversation history
        user_utt: User utterance
    """
    tool_hard_timeout_ms = float(os.getenv("TOOL_HARD_TIMEOUT_MS", "300"))

    # Run tool router (do not mark active to avoid clobbering chat req id)
    tool_req_id = f"tool-{uuid.uuid4()}"
    session_manager.set_tool_request(session_id, tool_req_id)
    tool_coro = run_toolcall(session_id, user_utt, history_text, request_id=tool_req_id, mark_active=False)

    tool_res = None
    try:
        if tool_hard_timeout_ms < 0:
            tool_res = await tool_coro
        else:
            tool_res = await asyncio.wait_for(tool_coro, timeout=tool_hard_timeout_ms / 1000.0)
    except asyncio.TimeoutError:
        # Best-effort abort underlying tool request
        try:
            if session_manager.session_tool_req.get(session_id):
                await (await get_tool_engine()).abort_request(
                    session_manager.session_tool_req.get(session_id, "")
                )
        except Exception:
            pass
        tool_res = {"cancelled": True}

    # Parse tool decision
    raw_field, is_tool = parse_tool_result(tool_res)

    # Cleanup tool req id tracking (no longer in-flight)
    try:
        session_manager.session_tool_req.pop(session_id, None)
    except Exception:
        pass

    if is_tool:
        # Tool detected: send toolcall response but continue with chat
        await ws.send_text(json.dumps({
            "type": "toolcall", 
            "status": "yes", 
            "raw": raw_field
        }))
    else:
        # Tool says NO (or timed out): notify client
        await ws.send_text(json.dumps({
            "type": "toolcall", 
            "status": "no", 
            "raw": raw_field
        }))

    # Start chat stream (always runs regardless of tool decision)
    chat_req_id = f"chat-{uuid.uuid4()}"
    session_manager.set_active_request(session_id, chat_req_id)
    final_text = ""
    
    async for chunk in run_chat_stream(
        session_id,
        static_prefix,
        runtime_text,
        history_text,
        user_utt,
        request_id=chat_req_id,
    ):
        await ws.send_text(json.dumps({"type": "token", "text": chunk}))
        final_text += chunk

    # Send final text as-is
    await ws.send_text(json.dumps({
        "type": "final", 
        "normalized_text": final_text
    }))
    await ws.send_text(json.dumps({"type": "done", "usage": {}}))
