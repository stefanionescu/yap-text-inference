"""Unified turn handler for both ``start`` and ``message`` payloads."""

from __future__ import annotations

import copy
import time
import logging
from fastapi import WebSocket
from src.state import TurnPlan
from typing import Any, Literal
from collections.abc import Callable
from .tasks import spawn_session_task
from src.config import CHAT_PROMPT_MAX_TOKENS
from src.config.websocket import WS_STATUS_OK
from .start.dispatch import dispatch_execution
from src.telemetry.sentry import capture_error
from src.runtime.dependencies import RuntimeDeps
from src.handlers.websocket.errors import send_error
from src.handlers.websocket.helpers import safe_send_flat
from .start.sampling import extract_sampling_overrides
from src.handlers.session.manager import SessionHandler
from .input import normalize_gender, normalize_personality
from src.handlers.session.config import update_session_config
from src.telemetry.phases import record_phase_error, record_phase_latency
from .plan_builders import _build_message_turn_plan
from .start.history import resolve_history
from src.config.websocket import WS_ERROR_INVALID_MESSAGE, WS_ERROR_INVALID_PAYLOAD, WS_ERROR_INVALID_SETTINGS
from .validators import (
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
    logger.info("turn_validation: error=%s; connection closed", err.error_code)


async def _send_turn_error(ws: WebSocket, *, code: str, message: str, close: bool = False) -> None:
    await send_error(ws, code=code, message=message)
    if close:
        await ws.close(code=1008)


def _validate_persona(msg: dict[str, Any], *, deploy_chat: bool) -> tuple[str | None, str | None]:
    if not deploy_chat:
        gender = normalize_gender(msg.get("gender"))
        personality = normalize_personality(msg.get("personality"))
        return gender, personality
    gender = validate_required_gender(msg.get("gender"))
    personality = validate_required_personality(msg.get("personality"))
    return gender, personality


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
    gender, personality = _validate_persona(msg, deploy_chat=deploy_chat)
    chat_prompt = _extract_chat_prompt(msg, count_tokens_fn=count_tokens_fn, deploy_chat=deploy_chat)
    sampling_overrides = extract_sampling_overrides(msg, deploy_chat=deploy_chat)
    check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(msg)
    return gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix


async def _bootstrap_start_turn(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    session_handler: SessionHandler,
) -> bool:
    t0 = time.perf_counter()
    try:
        session_handler.initialize_session(state)
        deploy_chat = session_handler.history_config.deploy_chat
        logger.info(
            "WS recv: start gender=%s len(history)=%s",
            msg.get("gender"),
            len(msg.get("history", [])),
        )

        try:
            gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix = (
                _resolve_start_inputs(
                    msg,
                    count_tokens_fn=session_handler.count_chat_tokens,
                    deploy_chat=deploy_chat,
                )
            )
        except ValidationError as err:
            capture_error(err)
            record_phase_error("validate", "invalid_start")
            await _close_with_validation_error(ws, err)
            return False

        sampling_payload = sampling_overrides if deploy_chat else None
        if deploy_chat and sampling_payload is None:
            sampling_payload = {}
        update_session_config(
            state,
            count_prefix_tokens_fn=session_handler._count_prefix_tokens,
            chat_gender=gender,
            chat_personality=personality,
            chat_prompt=chat_prompt,
            chat_sampling=sampling_payload,
            check_screen_prefix=check_screen_prefix,
            screen_checked_prefix=screen_checked_prefix,
        )
        resolve_history(session_handler, state, msg)
        await safe_send_flat(ws, "done", status=WS_STATUS_OK)
        return True
    finally:
        record_phase_latency("validate", time.perf_counter() - t0)


async def _plan_message_turn(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    session_handler: SessionHandler,
) -> TurnPlan | None:
    t0 = time.perf_counter()
    try:
        deploy_chat = session_handler.history_config.deploy_chat
        deploy_tool = session_handler.history_config.deploy_tool
        incoming_user_utt = (msg.get("user_utterance") or "").strip()
        if not incoming_user_utt:
            record_phase_error("validate", "missing_user_utterance")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_PAYLOAD, message="user_utterance is required")
            return None

        cfg = copy.deepcopy(state.meta)
        if not cfg:
            record_phase_error("validate", "missing_session")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_MESSAGE, message="no active session; send 'start' first")
            return None

        try:
            sampling_overrides = extract_sampling_overrides(msg, deploy_chat=deploy_chat)
        except ValidationError as err:
            record_phase_error("validate", "invalid_sampling")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_PAYLOAD, message=err.message, close=True)
            return None

        if sampling_overrides:
            update_session_config(
                state,
                count_prefix_tokens_fn=session_handler._count_prefix_tokens,
                chat_sampling=sampling_overrides,
            )

        return _build_message_turn_plan(
            state,
            cfg,
            incoming_user_utt,
            deploy_chat=deploy_chat,
            deploy_tool=deploy_tool,
            session_handler=session_handler,
            sampling_overrides=sampling_overrides,
        )
    finally:
        record_phase_latency("validate", time.perf_counter() - t0)


async def handle_turn_message(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    msg_type: Literal["start", "message"],
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> bool:
    """Handle one session turn message by planning + dispatching execution."""
    if msg_type == "start":
        return await _bootstrap_start_turn(ws, msg, state, session_handler=session_handler)

    plan = await _plan_message_turn(ws, msg, state, session_handler=session_handler)
    if plan is None:
        return False

    await spawn_session_task(
        ws,
        state,
        request_id=plan.request_id,
        operation=dispatch_execution(ws, plan, runtime_deps),
        session_handler=session_handler,
    )
    return True


__all__ = ["handle_turn_message"]
