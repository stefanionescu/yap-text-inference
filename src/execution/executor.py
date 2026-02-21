"""Executor: tool-first, then chat.

This module implements the main execution workflow that processes user messages
through a sequential tool-then-chat pipeline:

1. Tool Router Phase:
   - Launch tool request in parallel
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
- Tool model (fast intent detection)
- Session handler (history, persona, request tracking)
- Chat engine (streaming text generation)
- WebSocket helpers (response streaming)
"""

import asyncio
import logging
from fastapi import WebSocket
from .chat import run_chat_generation
from src.engines.base import BaseEngine
from src.tool.adapter import ToolAdapter
from .tool.parser import parse_tool_result
from ..config.timeouts import TOOL_TIMEOUT_S
from .tool.runner import launch_tool_request
from src.tokens.tokenizer import FastTokenizer
from src.telemetry.sentry import add_breadcrumb
from src.telemetry.instruments import get_metrics
from src.handlers.session.manager import SessionHandler
from ..handlers.websocket.helpers import cancel_task, send_toolcall, stream_chat_response

logger = logging.getLogger(__name__)


async def _await_tool_decision(
    session_id: str,
    user_utt: str,
    *,
    session_handler: SessionHandler,
    tool_adapter: ToolAdapter,
) -> tuple[str, bool]:
    tool_req_id, tool_task = launch_tool_request(
        session_id,
        user_utt,
        session_handler=session_handler,
        tool_adapter=tool_adapter,
    )
    logger.info("sequential_exec: tool start req_id=%s", tool_req_id)
    try:
        tool_res = await asyncio.wait_for(tool_task, timeout=TOOL_TIMEOUT_S)
    except TimeoutError:
        m = get_metrics()
        m.errors_total.add(1, {"error.type": "timeout"})
        add_breadcrumb("Tool timeout", category="execution", data={"timeout_s": TOOL_TIMEOUT_S})
        logger.warning(
            "sequential_exec: tool timeout session_id=%s req_id=%s timeout_s=%.1f",
            session_id,
            tool_req_id,
            TOOL_TIMEOUT_S,
        )
        await cancel_task(tool_task)
        tool_res = {"cancelled": True, "text": "[]", "timeout": True}
    finally:
        session_handler.clear_tool_request_id(session_id)
    raw_field, is_tool = parse_tool_result(tool_res)
    return raw_field, is_tool


async def _send_toolcall_status(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    raw_field: str,
    is_tool: bool,
) -> None:
    decision = "yes" if is_tool else "no"
    await send_toolcall(ws, session_id, request_id, decision, raw_field)
    logger.info("sequential_exec: sent toolcall %s", decision)


def _resolve_user_utterance_for_chat(
    session_id: str,
    user_utt: str,
    is_tool: bool,
    *,
    session_handler: SessionHandler,
) -> str:
    if not is_tool:
        return user_utt
    prefix = session_handler.get_check_screen_prefix(session_id)
    return f"{prefix} {user_utt}".strip()


async def run_execution(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    *,
    history_turn_id: str | None = None,
    sampling_overrides: dict[str, float | int] | None = None,
    session_handler: SessionHandler,
    chat_engine: BaseEngine,
    chat_tokenizer: FastTokenizer,
    tool_adapter: ToolAdapter,
) -> None:
    """Execute sequential tool-then-chat workflow.

    This is the main entry point for processing a user message. It:
    1. Launches tool model to detect intent
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
    raw_field, is_tool = await _await_tool_decision(
        session_id,
        user_utt,
        session_handler=session_handler,
        tool_adapter=tool_adapter,
    )
    await _send_toolcall_status(ws, session_id, request_id, raw_field, is_tool)

    # Start chat stream (for take_screenshot or no tool call)
    session_handler.set_active_request(session_id, request_id)
    user_utt_for_chat = _resolve_user_utterance_for_chat(
        session_id,
        user_utt,
        is_tool,
        session_handler=session_handler,
    )

    final_text = await stream_chat_response(
        ws,
        run_chat_generation(
            session_id,
            static_prefix,
            runtime_text,
            history_text,
            user_utt_for_chat,
            engine=chat_engine,
            session_handler=session_handler,
            chat_tokenizer=chat_tokenizer,
            request_id=request_id,
            sampling_overrides=sampling_overrides,
        ),
        session_id,
        request_id,
        user_utt_for_chat,
        history_turn_id=history_turn_id,
        history_user_utt=user_utt,
        session_handler=session_handler,
    )
    logger.info("sequential_exec: done chars=%s", len(final_text))


__all__ = ["run_execution"]
