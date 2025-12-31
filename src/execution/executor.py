"""Executor: tool-first, then chat.

This module implements the main execution workflow that processes user messages
through a sequential tool-then-chat pipeline:

1. Tool Router Phase:
   - Launch tool classifier request in parallel
   - Detect user intent (screenshot request, control function, or none)
   - Timeout handling with graceful fallback

2. Response Decision:
   - "take_screenshot": Prefix message with CHECK SCREEN, continue to chat
   - Control functions (switch_gender, etc.): Send hard-coded response
   - No tool match: Continue to chat without prefix

3. Chat Generation Phase:
   - Build prompt with persona + history + user message
   - Stream response via WebSocket
   - Record turn in session history

The executor coordinates between:
- Tool classifier (fast intent detection)
- Session handler (history, persona, request tracking)
- Chat engine (streaming text generation)
- WebSocket helpers (response streaming)
"""

import asyncio
import logging
import uuid
from fastapi import WebSocket

from .tool.parser import parse_tool_result
from .chat import run_chat_generation
from ..handlers.session import session_handler
from ..config.chat import CHAT_CONTINUE_TOOLS
from ..config.timeouts import TOOL_TIMEOUT_S
from ..handlers.websocket.helpers import (
    cancel_task,
    launch_tool_request,
    safe_send_json,
    send_toolcall,
    stream_chat_response,
)

logger = logging.getLogger(__name__)


def _should_skip_chat(raw_field: list | None) -> bool:
    """Determine if chat generation should be skipped based on tool result.
    
    Control functions like personality/gender switches don't need the chat
    model - they return hard-coded responses instead. This saves latency
    and GPU resources for simple control operations.
    
    Args:
        raw_field: Parsed tool result (list of tool dicts).
        
    Returns:
        True if any detected tool is NOT in CHAT_CONTINUE_TOOLS.
        
    Chat is skipped for:
        - switch_gender, switch_personality, switch_gender_and_personality
        - start_freestyle, stop_freestyle
        
    Chat continues for:
        - take_screenshot (needs CHECK SCREEN prefix)
        - Empty results (no tool detected)
    """
    if not raw_field or not isinstance(raw_field, list):
        return False
    
    # Check if any tool in the result is NOT in the continue set
    for item in raw_field:
        if isinstance(item, dict):
            name = item.get("name")
            if name and name not in CHAT_CONTINUE_TOOLS:
                return True
    
    return False


async def run_execution(
    ws: WebSocket,
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    *,
    history_turn_id: str | None = None,
    sampling_overrides: dict[str, float | int] | None = None,
) -> None:
    """Execute sequential tool-then-chat workflow.
    
    This is the main entry point for processing a user message. It:
    1. Launches tool classifier to detect intent
    2. Waits for tool result (with timeout)
    3. Sends toolcall status to client
    4. Either returns hard-coded response or streams chat generation
    
    Args:
        ws: WebSocket connection for sending responses.
        session_id: Session identifier for history/config lookup.
        static_prefix: Static persona system prompt prefix.
        runtime_text: Runtime persona context (timestamps, etc.).
        history_text: Conversation history in text format.
        user_utt: The user's message to process.
        history_turn_id: Optional existing turn ID for streaming updates.
        sampling_overrides: Optional sampling parameter overrides.
    """
    # Run tool router (do not mark active to avoid clobbering chat req id)
    # Timeout is handled internally by tool_runner.py (mirroring the chat stream)
    tool_req_id, tool_coro = launch_tool_request(session_id, user_utt)
    logger.info(f"sequential_exec: tool start req_id={tool_req_id}")

    try:
        tool_res = await asyncio.wait_for(tool_coro, timeout=TOOL_TIMEOUT_S)
    except asyncio.TimeoutError:
        logger.warning(
            "sequential_exec: tool timeout session_id=%s req_id=%s timeout_s=%.1f",
            session_id,
            tool_req_id,
            TOOL_TIMEOUT_S,
        )
        await cancel_task(tool_coro)
        tool_res = {"cancelled": True, "text": "[]", "timeout": True}

    # Parse tool decision
    raw_field, is_tool = parse_tool_result(tool_res)

    # Cleanup tool req id tracking (no longer in-flight)
    session_handler.clear_tool_request_id(session_id)

    if is_tool:
        # Tool detected: send toolcall response
        await send_toolcall(ws, "yes", raw_field)
        logger.info("sequential_exec: sent toolcall yes")
    else:
        # Tool says NO (or timed out): notify client
        await send_toolcall(ws, "no", raw_field)
        logger.info("sequential_exec: sent toolcall no")

    # Check if we should skip chat (control functions like switch_gender, etc.)
    if _should_skip_chat(raw_field):
        # Control function detected - use hard-coded message instead of chat model
        logger.info("sequential_exec: control function detected, using hard-coded response")
        # Pick a cycled control message for variety
        control_message = session_handler.pick_control_message(session_id)
        # Send the message as token + final + done
        await safe_send_json(ws, {"type": "token", "text": control_message})
        await safe_send_json(ws, {"type": "final", "normalized_text": control_message})
        await safe_send_json(ws, {"type": "done", "usage": {}})
        # Record both user utterance and control message in history
        session_handler.append_history_turn(session_id, user_utt, control_message)
        logger.info("sequential_exec: done (control function, msg=%r)", control_message)
        return

    # Start chat stream (for take_screenshot or no tool call)
    chat_req_id = f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, chat_req_id)
    # If tool said yes (take_screenshot), prefix the user utterance with CHECK SCREEN hint
    if is_tool:
        prefix = session_handler.get_check_screen_prefix(session_id)
        user_utt_for_chat = f"{prefix} {user_utt}".strip()
    else:
        user_utt_for_chat = user_utt

    final_text = await stream_chat_response(
        ws,
        run_chat_generation(
            session_id,
            static_prefix,
            runtime_text,
            history_text,
            user_utt_for_chat,
            request_id=chat_req_id,
            sampling_overrides=sampling_overrides,
        ),
        session_id,
        user_utt_for_chat,
        history_turn_id=history_turn_id,
        history_user_utt=user_utt,
    )
    logger.info(f"sequential_exec: done chars={len(final_text)}")
