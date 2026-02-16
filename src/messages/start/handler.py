"""Start message handler.

This module handles the 'start' WebSocket message type, which initiates
a new conversation turn. It validates inputs, sets up the session, and
dispatches the appropriate execution path.

The handler sends an 'ack' response immediately after validation,
then dispatches execution as a background task.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from fastapi import WebSocket

from src.state import StartPlan
from src.telemetry.sentry import capture_error
from src.runtime.dependencies import RuntimeDeps
from src.handlers.session.manager import SessionHandler

from ...tokens import count_tokens_chat
from .dispatch import dispatch_execution
from .sampling import extract_sampling_overrides
from ...handlers.websocket.errors import send_error
from ...config import DEPLOY_CHAT, CHAT_PROMPT_MAX_TOKENS
from .history import resolve_history, trim_user_utterance
from ..input import normalize_gender, normalize_personality
from ...handlers.websocket.helpers import safe_send_envelope
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
    session_id: str,
    request_id: str,
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
    await send_error(
        ws,
        session_id=session_id,
        request_id=request_id,
        error_code=error_code,
        message=err.message,
        reason_code=err.error_code,
    )
    await ws.close(code=1008)
    logger.info("handle_start: error → %s; connection closed", err.error_code)


def _resolve_start_inputs(
    payload: dict[str, Any],
) -> tuple[
    str | None,
    str | None,
    str | None,
    dict[str, float | int | bool],
    str | None,
    str | None,
]:
    gender, personality = _validate_persona(payload)
    chat_prompt = _extract_chat_prompt(payload)
    sampling_overrides = extract_sampling_overrides(payload)
    check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(payload)
    return gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix


def _update_start_session_config(
    *,
    session_handler: SessionHandler,
    session_id: str,
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
        session_id,
        chat_gender=gender,
        chat_personality=personality,
        chat_prompt=chat_prompt,
        chat_sampling=sampling_payload,
        check_screen_prefix=check_screen_prefix,
        screen_checked_prefix=screen_checked_prefix,
    )
    return session_handler.get_session_config(session_id)


def _prepare_turn_payload(
    session_handler: SessionHandler,
    session_id: str,
    payload: dict[str, Any],
    updated_config: dict[str, Any],
) -> tuple[str, str, str, str, dict[str, Any] | None, str | None]:
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text, history_info = resolve_history(session_handler, session_id, payload)
    user_utt = trim_user_utterance(session_handler, session_id, payload.get("user_utterance", ""))
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)
    return static_prefix, runtime_text, history_text, user_utt, history_info, history_turn_id


def _build_start_plan(
    *,
    session_id: str,
    request_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    history_turn_id: str | None,
    sampling_overrides: dict[str, float | int | bool],
) -> StartPlan:
    return StartPlan(
        session_id=session_id,
        request_id=request_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
    )


async def _send_start_ack(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    base_config: dict[str, Any],
    updated_config: dict[str, Any],
    history_info: dict[str, Any] | None,
) -> bool:
    sent = await safe_send_envelope(
        ws,
        msg_type="ack",
        session_id=session_id,
        request_id=request_id,
        payload=_build_ack_payload(session_id, base_config, updated_config, history_info),
    )
    if sent:
        logger.info("handle_start: ack sent session_id=%s", session_id)
    return sent


async def _resolve_start_inputs_or_close(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
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
        return _resolve_start_inputs(payload)
    except ValidationError as err:
        capture_error(err)
        await _close_with_validation_error(ws, session_id, request_id, err)
        return None


def _schedule_execution_task(
    ws: WebSocket,
    plan: StartPlan,
    runtime_deps: RuntimeDeps,
    session_handler: SessionHandler,
) -> None:
    task = asyncio.create_task(dispatch_execution(ws, plan, runtime_deps))
    session_handler.track_task(plan.session_id, task)


def _log_start_request(payload: dict[str, Any], session_id: str) -> None:
    logger.info(
        "handle_start: session_id=%s gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        session_id,
        payload.get("gender"),
        payload.get("personality"),
        len(payload.get("history", [])),
        len(payload.get("user_utterance", "")),
    )


async def handle_start_message(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    """Handle 'start' message type by validating inputs and dispatching execution.

    This is the main entry point for processing new conversation turns.

    Args:
        ws: WebSocket connection for responses.
        msg: Parsed message dict containing:
            - gender: Required, "male" or "female"
            - personality: Required, personality identifier
            - chat_prompt: Required if DEPLOY_CHAT, the system prompt
            - history: Optional, [{role, content}, ...] array
            - user_utterance: The user's message
            - sampling: Optional sampling parameter overrides
        session_id: Session identifier from the message.

    Side Effects:
        - Sends 'ack' response on success
        - Closes connection with error on validation failure
        - Spawns background task for execution
    """
    _log_start_request(payload, session_id)
    session_config = session_handler.initialize_session(session_id)

    resolved_inputs = await _resolve_start_inputs_or_close(
        ws,
        payload,
        session_id,
        request_id,
    )
    if resolved_inputs is None:
        return
    gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix = resolved_inputs

    updated_config = _update_start_session_config(
        session_handler=session_handler,
        session_id=session_id,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        sampling_overrides=sampling_overrides,
        check_screen_prefix=check_screen_prefix,
        screen_checked_prefix=screen_checked_prefix,
    )
    static_prefix, runtime_text, history_text, user_utt, history_info, history_turn_id = _prepare_turn_payload(
        session_handler,
        session_id,
        payload,
        updated_config,
    )

    if not await _send_start_ack(
        ws,
        session_id,
        request_id,
        session_config,
        updated_config,
        history_info,
    ):
        return

    plan = _build_start_plan(
        session_id=session_id,
        request_id=request_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=sampling_overrides,
    )

    _schedule_execution_task(ws, plan, runtime_deps, session_handler)


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


def _build_ack_payload(
    session_id: str,
    base_config: dict[str, Any],
    updated_config: dict[str, Any],
    history_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "for": "start",
        "ok": True,
        "now": base_config.get("now_str"),
        "gender": updated_config.get("chat_gender"),
        "personality": updated_config.get("chat_personality"),
        "chat_prompt": bool(updated_config.get("chat_prompt")),
    }
    if history_info is not None:
        payload["history"] = history_info
    return payload


__all__ = ["handle_start_message"]
