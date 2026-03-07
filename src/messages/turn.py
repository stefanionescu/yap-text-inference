"""Unified turn handler for both ``start`` and ``message`` payloads."""

from __future__ import annotations

import time
import uuid
import logging
import copy
from fastapi import WebSocket
from src.state import TurnPlan
from typing import Any, Literal
from collections.abc import Callable
from .tasks import spawn_session_task
from .start.dispatch import dispatch_execution
from src.telemetry.sentry import capture_error
from src.runtime.dependencies import RuntimeDeps
from src.handlers.websocket.errors import send_error
from src.handlers.session.config import update_session_config
from .start.sampling import extract_sampling_overrides
from src.handlers.session.manager import SessionHandler
from .input import normalize_gender, normalize_personality
from src.config import DEPLOY_CHAT, DEPLOY_TOOL, CHAT_PROMPT_MAX_TOKENS
from .start.history import resolve_history, resolve_user_utterances
from src.telemetry.phases import record_phase_error, record_phase_latency
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


def _validate_persona(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    if not DEPLOY_CHAT:
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
) -> str | None:
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
) -> tuple[
    str | None,
    str | None,
    str | None,
    dict[str, float | int | bool],
    str | None,
    str | None,
]:
    gender, personality = _validate_persona(msg)
    chat_prompt = _extract_chat_prompt(msg, count_tokens_fn=count_tokens_fn)
    sampling_overrides = extract_sampling_overrides(msg)
    check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(msg)
    return gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix


async def _plan_start_turn(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    session_handler: SessionHandler,
) -> TurnPlan | None:
    t0 = time.perf_counter()
    try:
        session_handler.initialize_session(state)
        logger.info(
            "WS recv: start gender=%s len(history)=%s len(user)=%s",
            msg.get("gender"),
            len(msg.get("history", [])),
            len(msg.get("user_utterance", "")),
        )

        try:
            gender, personality, chat_prompt, sampling_overrides, check_screen_prefix, screen_checked_prefix = (
                _resolve_start_inputs(msg, count_tokens_fn=session_handler.count_chat_tokens)
            )
        except ValidationError as err:
            capture_error(err)
            record_phase_error("validate", "invalid_start")
            await _close_with_validation_error(ws, err)
            return None

        sampling_payload = sampling_overrides if DEPLOY_CHAT else None
        if DEPLOY_CHAT and sampling_payload is None:
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
        cfg = copy.deepcopy(state.meta)

        history_turns = resolve_history(session_handler, state, msg)
        chat_user_utt, tool_user_utt = resolve_user_utterances(
            session_handler,
            state,
            msg.get("user_utterance", ""),
        )
        history_turn_id = session_handler.append_user_utterance(
            state,
            chat_user_utt,
            tool_user_utt=tool_user_utt,
        )
        plan_chat_user_utt = chat_user_utt if DEPLOY_CHAT else None
        static_prefix = cfg.get("chat_prompt") or ""
        return TurnPlan(
            state=state,
            request_id=f"start-{uuid.uuid4().hex}",
            static_prefix=static_prefix,
            runtime_text="",
            history_turns=history_turns,
            chat_user_utt=plan_chat_user_utt,
            tool_user_utt=tool_user_utt if DEPLOY_TOOL else None,
            history_turn_id=history_turn_id,
            sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
            apply_screen_checked_prefix=False,
        )
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
            sampling_overrides = extract_sampling_overrides(msg)
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

        apply_screen_checked_prefix = bool(state.screen_followup_pending)
        history_turns = session_handler._history.get_turns(state)
        chat_user_utt, tool_user_utt = resolve_user_utterances(
            session_handler,
            state,
            incoming_user_utt,
            for_followup=apply_screen_checked_prefix,
        )
        history_turn_id = session_handler.append_user_utterance(
            state,
            chat_user_utt,
            tool_user_utt=tool_user_utt,
        )
        plan_chat_user_utt = chat_user_utt if DEPLOY_CHAT else None
        static_prefix = cfg.get("chat_prompt") or ""
        return TurnPlan(
            state=state,
            request_id=f"msg-{uuid.uuid4().hex}",
            static_prefix=static_prefix,
            runtime_text="",
            history_turns=history_turns,
            chat_user_utt=plan_chat_user_utt,
            tool_user_utt=tool_user_utt if DEPLOY_TOOL else None,
            history_turn_id=history_turn_id,
            sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
            apply_screen_checked_prefix=apply_screen_checked_prefix,
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
) -> None:
    """Handle one session turn message by planning + dispatching execution."""
    if msg_type == "start":
        plan = await _plan_start_turn(ws, msg, state, session_handler=session_handler)
    else:
        plan = await _plan_message_turn(ws, msg, state, session_handler=session_handler)

    if plan is None:
        return

    await spawn_session_task(
        ws,
        state,
        request_id=plan.request_id,
        operation=dispatch_execution(ws, plan, runtime_deps),
        session_handler=session_handler,
    )


__all__ = ["handle_turn_message"]
