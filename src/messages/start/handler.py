"""Start message handler.

This module handles the 'start' WebSocket message type, which initiates
a new conversation turn. It validates inputs, sets up the session, and
dispatches the appropriate execution path.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from fastapi import WebSocket
from src.state import StartPlan
from ...tokens import count_tokens_chat
from .dispatch import dispatch_execution
from src.state.session import SessionState
from src.telemetry.sentry import capture_error
from .sampling import extract_sampling_overrides
from src.runtime.dependencies import RuntimeDeps
from ...handlers.websocket.errors import send_error
from src.handlers.session.manager import SessionHandler
from ...config import DEPLOY_CHAT, CHAT_PROMPT_MAX_TOKENS
from .history import resolve_history, trim_user_utterance
from ..input import normalize_gender, normalize_personality
from ...config.websocket import WS_ERROR_INVALID_PAYLOAD, WS_ERROR_INVALID_SETTINGS
from ..validators import (
    ValidationError,
    require_prompt,
    validate_optional_prefix,
    validate_required_gender,
    sanitize_prompt_with_limit,
    validate_required_personality,
)

logger = logging.getLogger(__name__)


async def _close_with_validation_error(
    ws: WebSocket,
    err: ValidationError,
) -> None:
    settings_errors = {
        "missing_chat_prompt",
        "invalid_chat_prompt",
        "chat_prompt_too_long",
        "invalid_check_screen_prefix",
        "invalid_screen_checked_prefix",
    }
    error_code = WS_ERROR_INVALID_SETTINGS if err.error_code in settings_errors else WS_ERROR_INVALID_PAYLOAD
    await send_error(ws, code=error_code, message=err.message)
    await ws.close(code=1008)
    logger.info("handle_start: error → %s; connection closed", err.error_code)


def _resolve_start_inputs(
    msg: dict[str, Any],
) -> tuple[
    str | None,
    str | None,
    str | None,
    dict[str, float | int | bool],
    str | None,
    str | None,
]:
    gender, personality = _validate_persona(msg)
    chat_prompt = _extract_chat_prompt(msg)
    sampling_overrides = extract_sampling_overrides(msg)
    check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(msg)
    return gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix


def _update_start_session_config(
    *,
    session_handler: SessionHandler,
    state: SessionState,
    gender: str | None,
    personality: str | None,
    chat_prompt: str | None,
    sampling_overrides: dict[str, float | int | bool],
    check_screen_prefix: str | None,
    screen_checked_prefix: str | None,
) -> dict[str, Any]:
    sampling_payload = sampling_overrides if DEPLOY_CHAT else None
    if DEPLOY_CHAT and sampling_payload is None:
        sampling_payload = {}
    session_handler.update_session_config(
        state,
        chat_gender=gender,
        chat_personality=personality,
        chat_prompt=chat_prompt,
        chat_sampling=sampling_payload,
        check_screen_prefix=check_screen_prefix,
        screen_checked_prefix=screen_checked_prefix,
    )
    return session_handler.get_session_config(state)


def _prepare_turn_payload(
    session_handler: SessionHandler,
    state: SessionState,
    msg: dict[str, Any],
    updated_config: dict[str, Any],
) -> tuple[str, str, str, str, str | None]:
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text = resolve_history(session_handler, state, msg)
    user_utt = trim_user_utterance(session_handler, state, msg.get("user_utterance", ""))
    history_turn_id = session_handler.append_user_utterance(state, user_utt)
    return static_prefix, runtime_text, history_text, user_utt, history_turn_id


def _build_start_plan(
    *,
    state: SessionState,
    request_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    history_turn_id: str | None,
    sampling_overrides: dict[str, float | int | bool],
) -> StartPlan:
    return StartPlan(
        state=state,
        request_id=request_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
    )


async def _resolve_start_inputs_or_close(
    ws: WebSocket,
    msg: dict[str, Any],
) -> (
    tuple[
        str | None,
        str | None,
        str | None,
        dict[str, float | int | bool],
        str | None,
        str | None,
    ]
    | None
):
    try:
        return _resolve_start_inputs(msg)
    except ValidationError as err:
        capture_error(err)
        await _close_with_validation_error(ws, err)
        return None


def _schedule_execution_task(
    ws: WebSocket,
    plan: StartPlan,
    runtime_deps: RuntimeDeps,
    session_handler: SessionHandler,
) -> None:
    task = asyncio.create_task(dispatch_execution(ws, plan, runtime_deps))
    session_handler.track_task(plan.state, task)


def _log_start_request(msg: dict[str, Any]) -> None:
    logger.info(
        "handle_start: gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        msg.get("gender"),
        msg.get("personality"),
        len(msg.get("history", [])),
        len(msg.get("user_utterance", "")),
    )


def _validate_persona(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    if not DEPLOY_CHAT:
        gender = normalize_gender(msg.get("gender"))
        personality = normalize_personality(msg.get("personality"))
        return gender, personality
    gender = validate_required_gender(msg.get("gender"))
    personality = validate_required_personality(msg.get("personality"))
    return gender, personality


def _extract_chat_prompt(msg: dict[str, Any]) -> str | None:
    raw_chat_prompt = msg.get("chat_prompt")
    if not DEPLOY_CHAT:
        return None
    required_chat_prompt = require_prompt(
        raw_chat_prompt,
        error_code="missing_chat_prompt",
        message="chat_prompt is required",
    )
    return sanitize_prompt_with_limit(
        required_chat_prompt,
        field_label="chat_prompt",
        invalid_error_code="invalid_chat_prompt",
        too_long_error_code="chat_prompt_too_long",
        max_tokens=CHAT_PROMPT_MAX_TOKENS,
        count_tokens_fn=count_tokens_chat,
    )


def _extract_screen_prefixes(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    check_prefix = validate_optional_prefix(
        msg.get("check_screen_prefix"),
        field_label="check_screen_prefix",
        invalid_error_code="invalid_check_screen_prefix",
    )
    screen_checked_prefix = validate_optional_prefix(
        msg.get("screen_checked_prefix"),
        field_label="screen_checked_prefix",
        invalid_error_code="invalid_screen_checked_prefix",
    )
    return check_prefix, screen_checked_prefix


async def handle_start_message(
    ws: WebSocket,
    msg: dict[str, Any],
    state: SessionState,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    """Handle 'start' message type by validating inputs and dispatching execution."""
    _log_start_request(msg)
    session_handler.initialize_session(state)

    resolved_inputs = await _resolve_start_inputs_or_close(ws, msg)
    if resolved_inputs is None:
        return
    gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix = resolved_inputs

    updated_config = _update_start_session_config(
        session_handler=session_handler,
        state=state,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        sampling_overrides=sampling_overrides,
        check_screen_prefix=check_screen_prefix,
        screen_checked_prefix=screen_checked_prefix,
    )
    static_prefix, runtime_text, history_text, user_utt, history_turn_id = _prepare_turn_payload(
        session_handler,
        state,
        msg,
        updated_config,
    )

    request_id = f"start-{id(state)}-{asyncio.get_event_loop().time():.0f}"
    plan = _build_start_plan(
        state=state,
        request_id=request_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=sampling_overrides,
    )

    _schedule_execution_task(ws, plan, runtime_deps, session_handler)


__all__ = ["handle_start_message"]
