"""Sequential execution: tool-first, then chat streaming."""

import asyncio
import logging
import uuid
from fastapi import WebSocket

from ..tool.tool_parser import parse_tool_result
from ..streaming.chat_streamer import run_chat_stream
from ...handlers.session_handler import session_handler
from ...config.timeouts import TOOL_HARD_TIMEOUT_MS
from ...utils.executor_utils import (
    abort_tool_request,
    launch_tool_request,
    send_toolcall,
    stream_chat_response,
)
from ...config import CHECK_SCREEN_PREFIX

logger = logging.getLogger(__name__)


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
    tool_hard_timeout_ms = float(TOOL_HARD_TIMEOUT_MS)
    logger.info(f"sequential_exec: session_id={session_id} tool_timeout_ms={tool_hard_timeout_ms}")

    # Run tool router (do not mark active to avoid clobbering chat req id)
    tool_req_id, tool_coro = launch_tool_request(session_id, user_utt, history_text)
    logger.info(f"sequential_exec: tool start req_id={tool_req_id}")

    tool_res = None
    try:
        if tool_hard_timeout_ms < 0:
            tool_res = await tool_coro
        else:
            tool_res = await asyncio.wait_for(tool_coro, timeout=tool_hard_timeout_ms / 1000.0)
    except asyncio.TimeoutError:
        await abort_tool_request(session_id)
        tool_res = {"cancelled": True}
        logger.info("sequential_exec: tool timeout → cancelled")

    # Parse tool decision
    raw_field, is_tool = parse_tool_result(tool_res)

    # Cleanup tool req id tracking (no longer in-flight)
    session_handler.clear_tool_request_id(session_id)

    if is_tool:
        # Tool detected: send toolcall response but continue with chat (CHECK SCREEN)
        await send_toolcall(ws, "yes", raw_field)
        logger.info("sequential_exec: sent toolcall yes")
    else:
        # Tool says NO (or timed out): notify client
        await send_toolcall(ws, "no", raw_field)
        logger.info("sequential_exec: sent toolcall no")

    # Start chat stream (always runs regardless of tool decision)
    chat_req_id = f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, chat_req_id)
    # If tool said yes, prefix the user utterance with CHECK SCREEN
    user_utt_for_chat = f"{CHECK_SCREEN_PREFIX} {user_utt}".strip() if is_tool else user_utt

    final_text = await stream_chat_response(
        ws,
        run_chat_stream(
            session_id,
            static_prefix,
            runtime_text,
            history_text,
            user_utt_for_chat,
            request_id=chat_req_id,
        ),
        session_id,
        user_utt_for_chat,
    )
    logger.info(f"sequential_exec: done chars={len(final_text)}")
