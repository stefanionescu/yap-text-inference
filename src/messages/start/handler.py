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

from .dispatch import dispatch_execution
from .sampling import extract_sampling_overrides
from ...handlers.instances import session_handler
from ...handlers.websocket.errors import send_error
from ..input import normalize_gender, normalize_personality
from ...handlers.websocket.helpers import safe_send_envelope
from ...config import DEPLOY_CHAT, DEPLOY_TOOL, CHAT_PROMPT_MAX_TOKENS
from ...config.websocket import WS_ERROR_INVALID_PAYLOAD, WS_ERROR_INVALID_SETTINGS
from ...tokens import count_tokens_chat, count_tokens_tool, trim_text_to_token_limit_chat, trim_text_to_token_limit_tool
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


async def handle_start_message(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
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
    logger.info(
        "handle_start: session_id=%s gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        session_id,
        payload.get("gender"),
        payload.get("personality"),
        len(payload.get("history", [])),
        len(payload.get("user_utterance", "")),
    )
    session_config = session_handler.initialize_session(session_id)

    try:
        gender, personality = _validate_persona(payload)
        chat_prompt = _extract_chat_prompt(payload)
        sampling_overrides = extract_sampling_overrides(payload)
        check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(payload)
    except ValidationError as err:
        await _close_with_validation_error(ws, session_id, request_id, err)
        return

    sampling_payload = None
    if DEPLOY_CHAT:
        sampling_payload = sampling_overrides if sampling_overrides else {}

    session_handler.update_session_config(
        session_id,
        chat_gender=gender,
        chat_personality=personality,
        chat_prompt=chat_prompt,
        chat_sampling=sampling_payload,
        check_screen_prefix=check_screen_prefix,
        screen_checked_prefix=screen_checked_prefix,
    )

    updated_config = session_handler.get_session_config(session_id)
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text, history_info = _resolve_history(session_id, payload)
    user_utt = _trim_user_utterance(payload.get("user_utterance", ""), session_id)
    # Track user utterance for pairing with assistant response later.
    # Don't re-fetch history_text - it already contains previous turns,
    # and user_utt is passed separately to the prompt builder.
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)

    if not await safe_send_envelope(
        ws,
        msg_type="ack",
        session_id=session_id,
        request_id=request_id,
        payload=_build_ack_payload(session_id, session_config, updated_config, history_info),
    ):
        return
    logger.info("handle_start: ack sent session_id=%s", session_id)

    plan = StartPlan(
        session_id=session_id,
        request_id=request_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
    )

    task = asyncio.create_task(dispatch_execution(ws, plan))
    session_handler.track_task(session_id, task)


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


def _resolve_history(session_id: str, msg: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    """Resolve history from message.

    Accepts: "history": [{role: "user", content: "..."}, ...]

    Returns:
        Tuple of (rendered_history_text, history_info_dict_or_none).
        history_info is only returned when warm history was sent.
    """
    if "history" in msg:
        history_messages = msg.get("history")
        if isinstance(history_messages, list):
            input_count = len(history_messages)
            rendered = session_handler.set_history_messages(session_id, history_messages)
            retained_count = session_handler.get_history_turn_count(session_id)
            history_tokens = _count_history_tokens(rendered)
            history_info = {
                "input_messages": input_count,
                "retained_turns": retained_count,
                "trimmed": retained_count < (input_count // 2),  # Rough heuristic: turns ≈ messages/2
                "history_tokens": history_tokens,
            }
            return rendered, history_info
    return session_handler.get_history_text(session_id), None


def _count_history_tokens(rendered: str) -> int:
    """Count history tokens using the appropriate tokenizer for the deployment mode."""
    if not rendered:
        return 0
    if DEPLOY_CHAT:
        return count_tokens_chat(rendered)
    if DEPLOY_TOOL:
        return count_tokens_tool(rendered)
    return 0


def _trim_user_utterance(user_utt: str, session_id: str) -> str:
    """Trim user utterance to token limit based on deployment mode."""
    effective_max = session_handler.get_effective_user_utt_max_tokens(session_id, for_followup=False)
    if DEPLOY_CHAT:
        return trim_text_to_token_limit_chat(user_utt, max_tokens=effective_max, keep="start")
    if DEPLOY_TOOL:
        return trim_text_to_token_limit_tool(user_utt, max_tokens=effective_max, keep="start")
    return user_utt or ""


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
