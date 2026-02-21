"""Follow-up handler to continue answer after external screen analysis.

Bypasses tool routing and directly invokes the chat model with a synthetic
user utterance built from the screenshot analysis and a configurable prefix.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import WebSocket
from ..config import DEPLOY_CHAT
from src.runtime.dependencies import RuntimeDeps
from ..handlers.websocket.errors import send_error
from ..tokens import trim_text_to_token_limit_chat
from ..execution.chat.runner import run_chat_generation
from src.handlers.session.manager import SessionHandler
from ..handlers.websocket.helpers import stream_chat_response
from ..config.websocket import WS_ERROR_INVALID_MESSAGE, WS_ERROR_INVALID_PAYLOAD, WS_ERROR_INVALID_SETTINGS

logger = logging.getLogger(__name__)


async def _send_followup_error(
    ws: WebSocket,
    *,
    session_id: str,
    request_id: str,
    error_code: str,
    message: str,
    reason_code: str,
) -> None:
    await send_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=error_code,
        message=message,
        reason_code=reason_code,
    )


async def _get_session_config(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    *,
    session_handler: SessionHandler,
) -> dict[str, Any] | None:
    cfg = session_handler.get_session_config(session_id)
    if cfg:
        return cfg
    await _send_followup_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=WS_ERROR_INVALID_MESSAGE,
        message="no active session; send 'start' first",
        reason_code="no_active_session",
    )
    return None


async def _extract_analysis_text(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
) -> str | None:
    analysis_text = (payload.get("analysis_text") or "").strip()
    if analysis_text:
        return analysis_text
    await _send_followup_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=WS_ERROR_INVALID_PAYLOAD,
        message="analysis_text is required",
        reason_code="missing_analysis_text",
    )
    return None


async def _resolve_chat_prompt(
    ws: WebSocket,
    cfg: dict[str, Any],
    session_id: str,
    request_id: str,
) -> str | None:
    static_prefix = cfg.get("chat_prompt") or ""
    if static_prefix:
        return static_prefix
    await _send_followup_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=WS_ERROR_INVALID_SETTINGS,
        message="chat_prompt must be set in session (send in start)",
        reason_code="missing_chat_prompt",
    )
    return None


def _build_followup_user_utterance(
    session_handler: SessionHandler,
    session_id: str,
    analysis_text: str,
) -> tuple[str, str, str | None]:
    prefix = session_handler.get_screen_checked_prefix(session_id)
    effective_max = session_handler.get_effective_user_utt_max_tokens(session_id, for_followup=True)
    trimmed_analysis = trim_text_to_token_limit_chat(analysis_text, max_tokens=effective_max, keep="start")
    user_utt = f"{prefix} {trimmed_analysis}".strip()
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)
    return user_utt, trimmed_analysis, history_turn_id


async def _validate_chat_runtime(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    runtime_deps: RuntimeDeps,
) -> bool:
    if runtime_deps.chat_engine is not None and runtime_deps.chat_tokenizer is not None:
        return True
    await _send_followup_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=WS_ERROR_INVALID_SETTINGS,
        message="chat runtime dependencies are not initialized",
        reason_code="chat_runtime_unavailable",
    )
    return False


async def _stream_followup_response(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    static_prefix: str,
    history_text: str,
    user_utt: str,
    trimmed_analysis: str,
    history_turn_id: str | None,
    sampling_overrides: Any,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    assert runtime_deps.chat_engine is not None  # noqa: S101
    assert runtime_deps.chat_tokenizer is not None  # noqa: S101
    await stream_chat_response(
        ws,
        run_chat_generation(
            session_id=session_id,
            static_prefix=static_prefix,
            runtime_text="",
            history_text=history_text,
            user_utt=user_utt,
            engine=runtime_deps.chat_engine,
            session_handler=session_handler,
            chat_tokenizer=runtime_deps.chat_tokenizer,
            request_id=request_id,
            sampling_overrides=sampling_overrides,
        ),
        session_id,
        request_id,
        user_utt,
        history_turn_id=history_turn_id,
        history_user_utt=trimmed_analysis,
        session_handler=session_handler,
    )


async def handle_followup_message(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    """Handle 'followup' message to continue with chat-only using analysis.

    Required fields:
        - analysis_text: str

    Optional fields:
        - user_identity: str
        - user_utterance: str (ignored for synthesis; may be used by clients)
    """
    if not DEPLOY_CHAT:
        await _send_followup_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_SETTINGS,
            message="followup requires chat model deployment",
            reason_code="followup_unavailable",
        )
        return

    cfg = await _get_session_config(
        ws,
        session_id,
        request_id,
        session_handler=session_handler,
    )
    if cfg is None:
        return

    analysis_text = await _extract_analysis_text(ws, payload, session_id, request_id)
    if analysis_text is None:
        return

    history_text = session_handler.get_history_text(session_id)
    static_prefix = await _resolve_chat_prompt(ws, cfg, session_id, request_id)
    if static_prefix is None:
        return

    user_utt, trimmed_analysis, history_turn_id = _build_followup_user_utterance(
        session_handler,
        session_id,
        analysis_text,
    )

    sampling_overrides = cfg.get("chat_sampling")
    if not await _validate_chat_runtime(ws, session_id, request_id, runtime_deps):
        return

    await _stream_followup_response(
        ws,
        session_id,
        request_id,
        static_prefix,
        history_text,
        user_utt,
        trimmed_analysis,
        history_turn_id,
        sampling_overrides,
        session_handler,
        runtime_deps,
    )
