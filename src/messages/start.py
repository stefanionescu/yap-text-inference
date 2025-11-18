"""Start message handler."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket

from ..config import (
    USER_UTT_MAX_TOKENS,
    CONCURRENT_MODEL_CALL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CHAT_PROMPT_MAX_TOKENS,
    TOOL_PROMPT_MAX_TOKENS,
    CHAT_TEMPERATURE_MIN,
    CHAT_TEMPERATURE_MAX,
    CHAT_TOP_P_MIN,
    CHAT_TOP_P_MAX,
    CHAT_TOP_K_MIN,
    CHAT_TOP_K_MAX,
    CHAT_MIN_P_MIN,
    CHAT_MIN_P_MAX,
    CHAT_REPEAT_PENALTY_MIN,
    CHAT_REPEAT_PENALTY_MAX,
    CHAT_PRESENCE_PENALTY_MIN,
    CHAT_PRESENCE_PENALTY_MAX,
    CHAT_FREQUENCY_PENALTY_MIN,
    CHAT_FREQUENCY_PENALTY_MAX,
)
from ..tokens import (
    count_tokens_chat,
    count_tokens_tool,
    trim_text_to_token_limit_chat,
    trim_text_to_token_limit_tool,
)
from ..handlers.session_handler import session_handler
from ..execution.executors.sequential_executor import run_sequential_execution
from ..execution.executors.concurrent_executor import run_concurrent_execution
from ..execution.streaming.chat_streamer import run_chat_stream
from ..execution.tool.tool_runner import run_toolcall
from ..execution.tool.tool_parser import parse_tool_result
from ..utils.executor_utils import stream_chat_response
from .validators import (
    ValidationError,
    require_prompt,
    sanitize_prompt_with_limit,
    validate_required_gender,
    validate_required_personality,
)


logger = logging.getLogger(__name__)

_SAMPLING_FIELDS: tuple[tuple[str, type, float | int, float | int, str, str], ...] = (
    ("temperature", float, CHAT_TEMPERATURE_MIN, CHAT_TEMPERATURE_MAX, "invalid_temperature", "temperature_out_of_range"),
    ("top_p", float, CHAT_TOP_P_MIN, CHAT_TOP_P_MAX, "invalid_top_p", "top_p_out_of_range"),
    ("top_k", int, CHAT_TOP_K_MIN, CHAT_TOP_K_MAX, "invalid_top_k", "top_k_out_of_range"),
    ("min_p", float, CHAT_MIN_P_MIN, CHAT_MIN_P_MAX, "invalid_min_p", "min_p_out_of_range"),
    ("repeat_penalty", float, CHAT_REPEAT_PENALTY_MIN, CHAT_REPEAT_PENALTY_MAX, "invalid_repeat_penalty", "repeat_penalty_out_of_range"),
    ("presence_penalty", float, CHAT_PRESENCE_PENALTY_MIN, CHAT_PRESENCE_PENALTY_MAX, "invalid_presence_penalty", "presence_penalty_out_of_range"),
    ("frequency_penalty", float, CHAT_FREQUENCY_PENALTY_MIN, CHAT_FREQUENCY_PENALTY_MAX, "invalid_frequency_penalty", "frequency_penalty_out_of_range"),
)


async def _close_with_validation_error(ws: WebSocket, err: ValidationError) -> None:
    await ws.send_text(json.dumps({
        "type": "error",
        "error_code": err.error_code,
        "message": err.message,
    }))
    await ws.close(code=1008)
    logger.info("handle_start: error → %s; connection closed", err.error_code)


@dataclass(slots=True)
class StartPlan:
    session_id: str
    static_prefix: str
    runtime_text: str
    history_text: str
    user_utt: str
    history_turn_id: str | None = None
    sampling_overrides: dict[str, float | int] | None = None


async def handle_start_message(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    """Handle 'start' message type by validating inputs and dispatching execution."""
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
        chat_prompt, tool_prompt = _extract_prompts(msg)
        sampling_overrides = _extract_sampling_overrides(msg)
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
        tool_prompt=tool_prompt,
        chat_sampling=sampling_payload,
    )

    updated_config = session_handler.get_session_config(session_id)
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text = _resolve_history(session_id, msg)
    user_utt = _trim_user_utterance(msg.get("user_utterance", ""))
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)
    history_text = session_handler.get_history_text(session_id)

    await ws.send_text(json.dumps(_build_ack_payload(session_id, session_config, updated_config)))
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

    task = asyncio.create_task(_dispatch_execution(ws, plan))
    session_handler.track_task(session_id, task)


def _validate_persona(msg: dict[str, Any]) -> tuple[str, str]:
    gender = validate_required_gender(msg.get("gender"))
    personality = validate_required_personality(msg.get("personality"))
    return gender, personality


def _extract_prompts(msg: dict[str, Any]) -> tuple[str | None, str | None]:
    chat_prompt = None
    tool_prompt = None

    raw_chat_prompt = msg.get("chat_prompt") or msg.get("persona_text")
    raw_tool_prompt = msg.get("tool_prompt")

    if DEPLOY_CHAT:
        required_chat_prompt = require_prompt(
            raw_chat_prompt,
            error_code="missing_chat_prompt",
            message="chat_prompt is required",
        )
        chat_prompt = sanitize_prompt_with_limit(
            required_chat_prompt,
            field_label="chat_prompt",
            invalid_error_code="invalid_chat_prompt",
            too_long_error_code="chat_prompt_too_long",
            max_tokens=CHAT_PROMPT_MAX_TOKENS,
            count_tokens_fn=count_tokens_chat,
        )

    if DEPLOY_TOOL:
        required_tool_prompt = require_prompt(
            raw_tool_prompt,
            error_code="missing_tool_prompt",
            message="tool_prompt is required",
        )
        tool_prompt = sanitize_prompt_with_limit(
            required_tool_prompt,
            field_label="tool_prompt",
            invalid_error_code="invalid_tool_prompt",
            too_long_error_code="tool_prompt_too_long",
            max_tokens=TOOL_PROMPT_MAX_TOKENS,
            count_tokens_fn=count_tokens_tool,
        )

    return chat_prompt, tool_prompt


def _resolve_history(session_id: str, msg: dict[str, Any]) -> str:
    if "history_text" in msg:
        incoming_history = msg.get("history_text") or ""
        return session_handler.set_history_text(session_id, incoming_history)
    return session_handler.get_history_text(session_id)


def _trim_user_utterance(user_utt: str) -> str:
    if DEPLOY_CHAT:
        return trim_text_to_token_limit_chat(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    if DEPLOY_TOOL:
        return trim_text_to_token_limit_tool(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    return user_utt or ""


def _extract_sampling_overrides(msg: dict[str, Any]) -> dict[str, float | int]:
    if not DEPLOY_CHAT:
        return {}

    overrides: dict[str, float | int] = {}
    sampling_block = msg.get("sampling") or msg.get("sampling_params") or {}
    if sampling_block and not isinstance(sampling_block, dict):
        raise ValidationError("invalid_sampling_payload", "sampling must be an object")

    for field, caster, minimum, maximum, invalid_code, range_code in _SAMPLING_FIELDS:
        raw_value = None
        if isinstance(sampling_block, dict):
            raw_value = sampling_block.get(field)
        if raw_value is None:
            raw_value = msg.get(field)
        if raw_value is None:
            continue

        try:
            normalized = _coerce_sampling_value(raw_value, caster)
        except (TypeError, ValueError):
            raise ValidationError(invalid_code, f"{field} must be a valid {caster.__name__}") from None

        if not (minimum <= normalized <= maximum):
            raise ValidationError(
                range_code,
                f"{field} must be between {minimum} and {maximum}",
            )
        overrides[field] = normalized

    return overrides


def _coerce_sampling_value(value: Any, caster: type) -> float | int:
    if caster is int:
        return _coerce_int(value)
    return _coerce_float(value)


def _coerce_float(value: Any) -> float:
    if isinstance(value, bool):
        raise TypeError("bool not allowed")
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("empty string")
        return float(stripped)
    raise TypeError("unsupported type")


def _coerce_int(value: Any) -> int:
    if isinstance(value, bool):
        raise TypeError("bool not allowed")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("non-integer float")
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("empty string")
        return int(stripped)
    raise TypeError("unsupported type")


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


async def _dispatch_execution(ws: WebSocket, plan: StartPlan) -> None:
    if DEPLOY_CHAT and DEPLOY_TOOL:
        if CONCURRENT_MODEL_CALL:
            logger.info("handle_start: concurrent execution session_id=%s", plan.session_id)
            await run_concurrent_execution(
                ws,
                plan.session_id,
                plan.static_prefix,
                plan.runtime_text,
                plan.history_text,
                plan.user_utt,
                history_turn_id=plan.history_turn_id,
                sampling_overrides=plan.sampling_overrides,
            )
        else:
            logger.info("handle_start: sequential execution session_id=%s", plan.session_id)
            await run_sequential_execution(
                ws,
                plan.session_id,
                plan.static_prefix,
                plan.runtime_text,
                plan.history_text,
                plan.user_utt,
                history_turn_id=plan.history_turn_id,
                sampling_overrides=plan.sampling_overrides,
            )
        return

    if DEPLOY_CHAT and not DEPLOY_TOOL:
        logger.info("handle_start: chat-only streaming session_id=%s", plan.session_id)
        final_text = await stream_chat_response(
            ws,
            run_chat_stream(
                plan.session_id,
                plan.static_prefix,
                plan.runtime_text,
                plan.history_text,
                plan.user_utt,
                sampling_overrides=plan.sampling_overrides,
            ),
            plan.session_id,
            plan.user_utt,
            history_turn_id=plan.history_turn_id,
            history_user_utt=plan.user_utt,
        )
        logger.info("handle_start: chat-only done session_id=%s chars=%s", plan.session_id, len(final_text))
        return

    if DEPLOY_TOOL and not DEPLOY_CHAT:
        logger.info("handle_start: tool-only routing session_id=%s", plan.session_id)
        tool_res = await run_toolcall(plan.session_id, plan.user_utt, plan.history_text, mark_active=False)
        raw_field, is_tool = parse_tool_result(tool_res)
        await ws.send_text(json.dumps({
            "type": "toolcall",
            "status": "yes" if is_tool else "no",
            "raw": raw_field,
        }))
        await ws.send_text(json.dumps({"type": "final", "normalized_text": ""}))
        await ws.send_text(json.dumps({"type": "done", "usage": {}}))
        logger.info("handle_start: tool-only done session_id=%s is_tool=%s", plan.session_id, is_tool)
