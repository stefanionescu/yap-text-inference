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

from ..config import DEPLOY_CHAT, DEPLOY_TOOL, CHAT_PROMPT_MAX_TOKENS
from ..tokens import count_tokens_chat, trim_text_to_token_limit_chat, trim_text_to_token_limit_tool
from ..handlers.session import session_handler
from ..handlers.websocket.helpers import safe_send_json
from .dispatch import StartPlan, dispatch_execution
from .sampling import extract_sampling_overrides
from .validators import (
    ValidationError,
    require_prompt,
    sanitize_prompt_with_limit,
    validate_required_gender,
    validate_required_personality,
    validate_optional_prefix,
    validate_personalities_list,
    validate_personality_in_list,
)


logger = logging.getLogger(__name__)


async def _close_with_validation_error(ws: WebSocket, err: ValidationError) -> None:
    await safe_send_json(ws, {
        "type": "error",
        "error_code": err.error_code,
        "message": err.message,
    })
    await ws.close(code=1008)
    logger.info("handle_start: error → %s; connection closed", err.error_code)


async def handle_start_message(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    """Handle 'start' message type by validating inputs and dispatching execution.
    
    This is the main entry point for processing new conversation turns.
    
    Args:
        ws: WebSocket connection for responses.
        msg: Parsed message dict containing:
            - gender: Required, "male" or "female"
            - personality: Required, personality identifier
            - chat_prompt: Required if DEPLOY_CHAT, the system prompt
            - history_text: Optional, previous conversation
            - user_utterance: The user's message
            - sampling: Optional sampling parameter overrides
            - personalities: Required if DEPLOY_TOOL, personality mappings
        session_id: Session identifier from the message.
        
    Side Effects:
        - Sends 'ack' response on success
        - Closes connection with error on validation failure
        - Spawns background task for execution
    """
    logger.info(
        "handle_start: session_id=%s gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        session_id,
        msg.get("gender"),
        msg.get("personality"),
        len(msg.get("history_text", "")),
        len(msg.get("user_utterance", "")),
    )
    session_config = session_handler.initialize_session(session_id)

    try:
        gender, personality = _validate_persona(msg)
        chat_prompt = _extract_chat_prompt(msg)
        sampling_overrides = extract_sampling_overrides(msg)
        check_screen_prefix, screen_checked_prefix = _extract_screen_prefixes(msg)
        personalities = _extract_personalities(msg)
        # Validate that initial personality is in the personalities list
        validate_personality_in_list(personality, personalities)
    except ValidationError as err:
        await _close_with_validation_error(ws, err)
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
    
    # Store personalities for tool phrase matching
    if personalities is not None:
        session_handler.set_personalities(session_id, personalities)

    updated_config = session_handler.get_session_config(session_id)
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text = _resolve_history(session_id, msg)
    user_utt = _trim_user_utterance(msg.get("user_utterance", ""), session_id)
    # Track user utterance for pairing with assistant response later.
    # Don't re-fetch history_text - it already contains previous turns,
    # and user_utt is passed separately to the prompt builder.
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)

    if not await safe_send_json(ws, _build_ack_payload(session_id, session_config, updated_config)):
        return
    logger.info("handle_start: ack sent session_id=%s", session_id)

    plan = StartPlan(
        session_id=session_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if DEPLOY_CHAT else None,
    )

    task = asyncio.create_task(dispatch_execution(ws, plan))
    session_handler.track_task(session_id, task)


def _validate_persona(msg: dict[str, Any]) -> tuple[str, str]:
    gender = validate_required_gender(msg.get("gender"))
    personality = validate_required_personality(msg.get("personality"))
    return gender, personality


def _extract_chat_prompt(msg: dict[str, Any]) -> str | None:
    raw_chat_prompt = msg.get("chat_prompt") or msg.get("persona_text")
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


def _extract_personalities(msg: dict[str, Any]) -> dict[str, list[str]] | None:
    """Extract and validate personalities configuration.
    
    Required when DEPLOY_TOOL is enabled, optional otherwise.
    
    Expected format:
    {
        "friendly": ["generic", "normal"],
        "flirty": ["horny", "sexy"],
        "religious": [],
        "delulu": []
    }
    """
    raw_personalities = msg.get("personalities")
    
    # If DEPLOY_TOOL is enabled, personalities are required
    if DEPLOY_TOOL and raw_personalities is None:
        raise ValidationError(
            "missing_personalities",
            "personalities is required - must be an object mapping personality names to synonym arrays"
        )
    
    # Validate format if provided
    return validate_personalities_list(raw_personalities)


def _resolve_history(session_id: str, msg: dict[str, Any]) -> str:
    if "history_text" in msg:
        incoming_history = msg.get("history_text") or ""
        return session_handler.set_history_text(session_id, incoming_history)
    return session_handler.get_history_text(session_id)


def _trim_user_utterance(user_utt: str, session_id: str) -> str:
    """Trim user utterance to token limit based on deployment mode."""
    effective_max = session_handler.get_effective_user_utt_max_tokens(
        session_id, for_followup=False
    )
    if DEPLOY_CHAT:
        return trim_text_to_token_limit_chat(user_utt, max_tokens=effective_max, keep="start")
    if DEPLOY_TOOL:
        return trim_text_to_token_limit_tool(user_utt, max_tokens=effective_max, keep="start")
    return user_utt or ""


def _build_ack_payload(
    session_id: str,
    base_config: dict[str, Any],
    updated_config: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": "ack",
        "for": "start",
        "ok": True,
        "session_id": session_id,
        "now": base_config.get("now_str"),
        "gender": updated_config.get("chat_gender"),
        "personality": updated_config.get("chat_personality"),
        "chat_prompt": bool(updated_config.get("chat_prompt")),
    }


__all__ = ["handle_start_message"]
