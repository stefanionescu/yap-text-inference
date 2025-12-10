"""Executor: tool-first, then chat."""

import logging
import uuid
from fastapi import WebSocket

from .tool.parser import parse_tool_result
from .chat import run_chat_generation
from ..handlers.session import session_handler
from ..utils.executor import launch_tool_request, send_toolcall, stream_chat_response

logger = logging.getLogger(__name__)


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
    
    Args:
        ws: WebSocket connection
        session_id: Session identifier
        static_prefix: Static persona prefix
        runtime_text: Runtime persona text
        history_text: Conversation history
        user_utt: User utterance
    """
    # Run tool router (do not mark active to avoid clobbering chat req id)
    # Timeout is handled internally by tool_runner.py (mirroring the chat stream)
    tool_req_id, tool_coro = launch_tool_request(session_id, user_utt, history_text)
    logger.info(f"sequential_exec: tool start req_id={tool_req_id}")

    tool_res = await tool_coro

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
    # If tool said yes, prefix the user utterance with the session-specific CHECK SCREEN hint
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
