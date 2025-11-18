"""Start message handler split from message_handlers for modularity."""

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


async def handle_start_message(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    """Handle 'start' message type by validating inputs and dispatching execution."""
    logger.info(
        "handle_start: session_id=%s gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        session_id,
        msg.get("assistant_gender"),
        msg.get("personality"),
        len(msg.get("history_text", "")),
        len(msg.get("user_utterance", "")),
    )
    session_config = session_handler.initialize_session(session_id)

    try:
        gender, personality = _validate_persona(msg)
        chat_prompt, tool_prompt = _extract_prompts(msg)
    except ValidationError as err:
        await _close_with_validation_error(ws, err)
        return

    session_handler.update_session_config(
        session_id,
        chat_gender=gender,
        chat_personality=personality,
        chat_prompt=chat_prompt,
        tool_prompt=tool_prompt,
    )

    updated_config = session_handler.get_session_config(session_id)
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""
    history_text = _resolve_history(session_id, msg)
    user_utt = _trim_user_utterance(msg.get("user_utterance", ""))

    await ws.send_text(json.dumps(_build_ack_payload(session_id, session_config, updated_config)))
    logger.info("handle_start: ack sent session_id=%s", session_id)

    plan = StartPlan(
        session_id=session_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
    )

    task = asyncio.create_task(_dispatch_execution(ws, plan))
    session_handler.track_task(session_id, task)


def _validate_persona(msg: dict[str, Any]) -> tuple[str, str]:
    gender = validate_required_gender(msg.get("assistant_gender"))
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
        "assistant_gender": updated_config.get("chat_gender"),
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
            ),
            plan.session_id,
            plan.user_utt,
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


