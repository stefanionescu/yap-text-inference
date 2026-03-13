"""Start-message bootstrap for initializing a session turn."""

from __future__ import annotations

import time
import logging
from typing import Any
from fastapi import WebSocket
from .history import resolve_history
from collections.abc import Callable
from src.config import CHAT_PROMPT_MAX_TOKENS
from src.telemetry.sentry import capture_error
from .sampling import extract_sampling_overrides
from src.handlers.websocket.errors import send_error
from src.handlers.session.manager import SessionHandler
from src.handlers.websocket.helpers import safe_send_flat
from src.handlers.session.config import update_session_config
from src.telemetry.phases import record_phase_error, record_phase_latency
from src.config.websocket import (
    WS_STATUS_OK,
    WS_ERROR_TEXT_TOO_LONG,
    WS_ERROR_INVALID_PAYLOAD,
    WS_ERROR_INVALID_SETTINGS,
)
from .validators import (
    ValidationError,
    require_prompt,
    normalize_gender,
    normalize_personality,
    validate_optional_prefix,
    validate_required_gender,
    sanitize_prompt_with_limit,
    validate_required_personality,
)

logger = logging.getLogger(__name__)

_TOOL_ONLY_FORBIDDEN_START_FIELDS: tuple[str, ...] = (
    "gender",
    "personality",
    "chat_prompt",
    "sampling",
    "sampling_params",
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "repetition_penalty",
    "presence_penalty",
    "frequency_penalty",
    "sanitize_output",
)


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
        "tool_only_forbids_chat_settings",
    }
    error_code = WS_ERROR_INVALID_SETTINGS if err.error_code in settings_errors else WS_ERROR_INVALID_PAYLOAD
    await send_error(ws, code=error_code, message=err.message)
    await ws.close(code=1008)
    logger.info("turn_validation: error=%s; connection closed", err.error_code)


async def _send_turn_error(ws: WebSocket, *, code: str, message: str, close: bool = False) -> None:
    await send_error(ws, code=code, message=message)
    if close:
        await ws.close(code=1008)


def _validate_tool_only_start_fields(msg: dict[str, Any], *, deploy_chat: bool) -> None:
    if deploy_chat:
        return
    offending_fields = [field for field in _TOOL_ONLY_FORBIDDEN_START_FIELDS if field in msg]
    if offending_fields:
        raise ValidationError(
            "tool_only_forbids_chat_settings",
            "tool-only deployment does not accept chat-only start fields: " + ", ".join(offending_fields),
        )


def _validate_persona(msg: dict[str, Any], *, deploy_chat: bool) -> tuple[str | None, str | None]:
    if deploy_chat:
        return validate_required_gender(msg.get("gender")), validate_required_personality(msg.get("personality"))
    return normalize_gender(msg.get("gender")), normalize_personality(msg.get("personality"))


def _extract_chat_prompt(
    msg: dict[str, Any],
    *,
    count_tokens_fn: Callable[[str], int],
    deploy_chat: bool,
) -> str | None:
    raw_chat_prompt = msg.get("chat_prompt")
    if not deploy_chat:
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
        count_tokens_fn=count_tokens_fn,
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


def _resolve_start_inputs(
    msg: dict[str, Any],
    *,
    count_tokens_fn: Callable[[str], int],
    deploy_chat: bool,
) -> tuple[
    str | None,
    str | None,
    str | None,
    dict[str, float | int | bool],
    str | None,
    str | None,
]:
    _validate_tool_only_start_fields(msg, deploy_chat=deploy_chat)
    gender, personality = _validate_persona(msg, deploy_chat=deploy_chat)
    chat_prompt = _extract_chat_prompt(msg, count_tokens_fn=count_tokens_fn, deploy_chat=deploy_chat)
    sampling_overrides = extract_sampling_overrides(msg, deploy_chat=deploy_chat)
    check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(msg)
    return gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix


async def _resolve_start_inputs_or_reject(
    ws: WebSocket,
    msg: dict[str, Any],
    *,
    session_handler: SessionHandler,
    deploy_chat: bool,
) -> tuple[str | None, str | None, str | None, dict[str, float | int | bool], str | None, str | None] | None:
    try:
        return _resolve_start_inputs(
            msg,
            count_tokens_fn=session_handler.count_chat_tokens,
            deploy_chat=deploy_chat,
        )
    except ValidationError as err:
        capture_error(err)
        record_phase_error("validate", "invalid_start")
        await _close_with_validation_error(ws, err)
        return None


async def bootstrap_start_turn(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    session_handler: SessionHandler,
) -> bool:
    """Initialize a fresh session from a start payload."""
    t0 = time.perf_counter()
    try:
        session_handler.initialize_session(state)
        deploy_chat = session_handler.history_config.deploy_chat
        logger.info(
            "WS recv: start gender=%s len(history)=%s",
            msg.get("gender"),
            len(msg.get("history", [])),
        )

        resolved = await _resolve_start_inputs_or_reject(
            ws,
            msg,
            session_handler=session_handler,
            deploy_chat=deploy_chat,
        )
        if resolved is None:
            return False
        gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix = resolved

        sampling_payload = sampling_overrides if deploy_chat else None
        if deploy_chat and sampling_payload is None:
            sampling_payload = {}
        update_session_config(
            state,
            count_prefix_tokens_fn=session_handler.count_prefix_tokens,
            chat_gender=gender,
            chat_personality=personality,
            chat_prompt=chat_prompt,
            chat_sampling=sampling_payload,
            check_screen_prefix=check_screen_prefix,
            screen_checked_prefix=screen_checked_prefix,
        )
        resolve_history(session_handler, state, msg)
        if deploy_chat:
            try:
                session_handler.fit_start_chat_history(
                    state,
                    static_prefix=chat_prompt or "",
                    runtime_text="",
                )
            except ValueError as exc:
                record_phase_error("validate", "seed_history_too_long")
                await _send_turn_error(ws, code=WS_ERROR_TEXT_TOO_LONG, message=str(exc), close=True)
                return False
        await safe_send_flat(ws, "done", status=WS_STATUS_OK)
        return True
    finally:
        record_phase_latency("validate", time.perf_counter() - t0)


__all__ = ["bootstrap_start_turn"]
