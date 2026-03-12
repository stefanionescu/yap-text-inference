"""Executor: tool-first, then chat.

This module implements the main execution workflow that processes user messages
through a sequential tool-then-chat pipeline:

1. Tool Router Phase:
   - Launch tool request in parallel
   - Detect user intent (screenshot request, control function, or none)
   - Timeout handling with graceful fallback

2. Response Decision:
   - "take_screenshot": Prefix message with CHECK SCREEN, continue to chat
   - No tool match: Continue to chat without prefix

3. Chat Generation Phase:
   - Build prompt with persona + history + user message
   - Stream response via WebSocket
   - Record turn in session history
"""

import asyncio
import logging
from fastapi import WebSocket
from .chat import run_chat_generation
from src.engines.base import BaseEngine
from src.tool.adapter import ToolAdapter
from collections.abc import AsyncIterator
from .tool.parser import parse_tool_result
from ..config.timeouts import TOOL_TIMEOUT_S
from .tool.runner import launch_tool_request
from src.tokens.tokenizer import FastTokenizer
from src.telemetry.sentry import add_breadcrumb
from src.telemetry.instruments import get_metrics
from ..handlers.websocket.errors import send_error
from ..config.websocket import WS_ERROR_TEXT_TOO_LONG
from ..config import CHAT_MAX_LEN, USER_UTT_MAX_TOKENS
from src.handlers.session.manager import SessionHandler
from src.state.session import ChatMessage, SessionState
from src.handlers.session.config import resolve_screen_prefix
from .chat.prompt_budget import PromptFitResult, fit_chat_prompt_to_budget
from src.config import DEFAULT_CHECK_SCREEN_PREFIX, DEFAULT_SCREEN_CHECKED_PREFIX
from ..handlers.websocket.helpers import cancel_task, send_toolcall, stream_chat_response

logger = logging.getLogger(__name__)

PromptContext = tuple[str, str, list[ChatMessage]]
StreamContext = tuple[str, dict[str, float | int] | None, BaseEngine, FastTokenizer]


async def _await_tool_decision(
    state: SessionState,
    tool_user_utt: str,
    tool_user_history: str,
    *,
    tool_adapter: ToolAdapter,
) -> tuple[str, bool]:
    tool_req_id, tool_task = launch_tool_request(
        state,
        tool_user_utt=tool_user_utt,
        tool_user_history=tool_user_history,
        tool_adapter=tool_adapter,
    )
    logger.info("sequential_exec: tool start req_id=%s", tool_req_id)
    try:
        tool_res = await asyncio.wait_for(tool_task, timeout=TOOL_TIMEOUT_S)
    except TimeoutError:
        m = get_metrics()
        m.errors_total.add(1, {"error.type": "timeout"})
        add_breadcrumb("Tool timeout", category="execution", data={"timeout_s": TOOL_TIMEOUT_S})
        logger.warning("sequential_exec: tool timeout req_id=%s timeout_s=%.1f", tool_req_id, TOOL_TIMEOUT_S)
        await cancel_task(tool_task)
        tool_res = {"cancelled": True, "text": "[]", "timeout": True}
    raw_field, is_tool = parse_tool_result(tool_res)
    return raw_field, is_tool


async def _send_toolcall_status(
    ws: WebSocket,
    raw_field: str,
    is_tool: bool,
) -> None:
    tools = raw_field if is_tool else []
    await send_toolcall(ws, tools)
    logger.info("sequential_exec: sent toolcall %s", "yes" if is_tool else "no")


def _prepare_tool_turn(
    state: SessionState,
    chat_user_utt: str,
    *,
    tool_user_utt: str | None,
    history_turn_id: str | None,
    session_handler: SessionHandler,
) -> tuple[str, str]:
    effective_tool_user_utt = (tool_user_utt or chat_user_utt).strip()
    return session_handler.prepare_tool_turn(state, effective_tool_user_utt, turn_id=history_turn_id)


async def _resolve_tool_decision_and_send_status(
    ws: WebSocket,
    state: SessionState,
    tool_user_utt: str,
    tool_user_history: str,
    *,
    tool_adapter: ToolAdapter,
) -> bool:
    raw_field, is_tool = await _await_tool_decision(
        state,
        tool_user_utt,
        tool_user_history,
        tool_adapter=tool_adapter,
    )
    await _send_toolcall_status(ws, raw_field, is_tool)
    return is_tool


def _resolve_user_utterance_for_chat(
    state: SessionState,
    chat_user_utt: str,
    is_tool: bool,
    apply_screen_checked_prefix: bool,
    *,
    session_handler: SessionHandler,
) -> str:
    if is_tool:
        session_handler.set_screen_followup_pending(state, True)
        prefix = resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)
        return f"{prefix} {chat_user_utt}".strip()

    if apply_screen_checked_prefix:
        session_handler.set_screen_followup_pending(state, False)
        prefix = resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)
        return f"{prefix} {chat_user_utt}".strip()

    return chat_user_utt


async def _fit_chat_prompt_or_send_error(
    ws: WebSocket,
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_user_utt: str,
    *,
    chat_tokenizer: FastTokenizer,
) -> PromptFitResult | None:
    try:
        return fit_chat_prompt_to_budget(
            static_prefix,
            runtime_text,
            history_messages,
            chat_user_utt,
            chat_tokenizer,
            max_prompt_tokens=CHAT_MAX_LEN,
            max_user_tokens=USER_UTT_MAX_TOKENS,
        )
    except ValueError as exc:
        await send_error(ws, code=WS_ERROR_TEXT_TOO_LONG, message=str(exc))
        return None


async def _resolve_prompt_fit(
    ws: WebSocket,
    state: SessionState,
    prompt_context: PromptContext,
    chat_user_utt: str,
    is_tool: bool,
    *,
    apply_screen_checked_prefix: bool,
    session_handler: SessionHandler,
    chat_tokenizer: FastTokenizer,
) -> PromptFitResult | None:
    static_prefix, runtime_text, history_messages = prompt_context
    chat_user_utt_for_chat = _resolve_user_utterance_for_chat(
        state,
        chat_user_utt,
        is_tool,
        apply_screen_checked_prefix=apply_screen_checked_prefix,
        session_handler=session_handler,
    )
    return await _fit_chat_prompt_or_send_error(
        ws,
        static_prefix,
        runtime_text,
        history_messages,
        chat_user_utt_for_chat,
        chat_tokenizer=chat_tokenizer,
    )


async def _stream_chat_turn(
    ws: WebSocket,
    stream: AsyncIterator[str],
    state: SessionState,
    prompt_fit: PromptFitResult,
    *,
    history_turn_id: str | None,
    session_handler: SessionHandler,
) -> None:
    history_user_utt, _ = session_handler.normalize_user_utterances(state, prompt_fit.chat_user_utt)
    final_text = await stream_chat_response(
        ws,
        stream,
        state,
        prompt_fit.chat_user_utt,
        history_turn_id=history_turn_id,
        history_user_utt=history_user_utt,
        session_handler=session_handler,
    )
    logger.info("sequential_exec: done chars=%s", len(final_text))


def _build_chat_stream(
    state: SessionState,
    prompt_fit: PromptFitResult,
    stream_context: StreamContext,
) -> AsyncIterator[str]:
    request_id, sampling_overrides, chat_engine, chat_tokenizer = stream_context
    return run_chat_generation(
        state,
        prompt_fit.prompt,
        engine=chat_engine,
        chat_tokenizer=chat_tokenizer,
        request_id=request_id,
        sampling_overrides=sampling_overrides,
        prompt_token_count=prompt_fit.prompt_tokens,
    )


async def _run_fitted_chat_turn(
    ws: WebSocket,
    state: SessionState,
    prompt_fit: PromptFitResult,
    stream_context: StreamContext,
    *,
    history_turn_id: str | None,
    session_handler: SessionHandler,
) -> None:
    await _stream_chat_turn(
        ws,
        _build_chat_stream(state, prompt_fit, stream_context),
        state,
        prompt_fit,
        history_turn_id=history_turn_id,
        session_handler=session_handler,
    )


async def run_execution(
    ws: WebSocket,
    state: SessionState,
    request_id: str,
    static_prefix: str,
    runtime_text: str,
    history_messages: list[ChatMessage],
    chat_user_utt: str,
    *,
    tool_user_utt: str | None = None,
    history_turn_id: str | None = None,
    sampling_overrides: dict[str, float | int] | None = None,
    apply_screen_checked_prefix: bool = False,
    session_handler: SessionHandler,
    chat_engine: BaseEngine,
    chat_tokenizer: FastTokenizer,
    tool_adapter: ToolAdapter,
) -> None:
    """Execute sequential tool-then-chat workflow."""
    prompt_context: PromptContext = (static_prefix, runtime_text, history_messages)
    stream_context: StreamContext = (request_id, sampling_overrides, chat_engine, chat_tokenizer)
    effective_tool_user_utt, tool_user_history = _prepare_tool_turn(
        state,
        chat_user_utt,
        tool_user_utt=tool_user_utt,
        history_turn_id=history_turn_id,
        session_handler=session_handler,
    )
    is_tool = await _resolve_tool_decision_and_send_status(
        ws,
        state,
        effective_tool_user_utt,
        tool_user_history,
        tool_adapter=tool_adapter,
    )
    prompt_fit = await _resolve_prompt_fit(
        ws,
        state,
        prompt_context,
        chat_user_utt,
        is_tool,
        apply_screen_checked_prefix=apply_screen_checked_prefix,
        session_handler=session_handler,
        chat_tokenizer=chat_tokenizer,
    )
    if prompt_fit is None:
        return

    await _run_fitted_chat_turn(
        ws,
        state,
        prompt_fit,
        stream_context,
        history_turn_id=history_turn_id,
        session_handler=session_handler,
    )


__all__ = ["run_execution"]
