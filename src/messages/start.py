"""Start message handler split from message_handlers for modularity."""

import asyncio
import json
import logging
from typing import Any
from fastapi import WebSocket

from ..config import (
    USER_UTT_MAX_TOKENS,
    CONCURRENT_MODEL_CALL,
    DEPLOY_CHAT, DEPLOY_TOOL,
    CHAT_PROMPT_MAX_TOKENS, TOOL_PROMPT_MAX_TOKENS,
    PERSONALITY_MAX_LEN,
)
from ..tokens import (
    count_tokens_chat, count_tokens_tool,
    trim_text_to_token_limit_chat, trim_text_to_token_limit_tool,
)
from ..utils.validation import (
    normalize_gender,
    is_gender_empty_or_null,
    normalize_personality,
    is_personality_empty_or_null,
)
from ..utils.sanitize import sanitize_prompt
from ..handlers.session_handler import session_handler
from ..execution.sequential_executor import run_sequential_execution
from ..execution.concurrent_executor import run_concurrent_execution
from ..execution.chat_streamer import run_chat_stream
from ..execution.tool_runner import run_toolcall
from ..execution.tool_parser import parse_tool_result
from ..execution.executor_utils import stream_chat_response
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


async def handle_start_message(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    """Handle 'start' message type."""
    logger.info(
        "handle_start: session_id=%s gender_in=%s personality_in=%s hist_len=%s user_len=%s",
        session_id,
        msg.get("assistant_gender"),
        msg.get("personality"),
        len(msg.get("history_text", "")),
        len(msg.get("user_utterance", "")),
    )
    session_config = session_handler.initialize_session(session_id)

    # Pull fixed values for this session
    sess_now_str = session_config["now_str"]

    # Require assistant_gender and personality at start; validate them first
    raw_gender = msg.get("assistant_gender")
    raw_personality = msg.get("personality")

    try:
        incoming_gender = validate_required_gender(raw_gender)
        incoming_personality = validate_required_personality(raw_personality)
    except ValidationError as err:
        await _close_with_validation_error(ws, err)
        return

    session_handler.update_session_config(
        session_id,
        chat_gender=incoming_gender,
        chat_personality=incoming_personality,
    )

    # Require client-provided prompts depending on deployment mode
    # chat prompt alias: allow legacy 'persona_text'
    raw_chat_prompt = msg.get("chat_prompt") or msg.get("persona_text")
    raw_tool_prompt = msg.get("tool_prompt")

    try:
        chat_prompt = None
        tool_prompt = None
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
    except ValidationError as err:
        await _close_with_validation_error(ws, err)
        return

    if chat_prompt is not None:
        session_handler.update_session_config(session_id, chat_prompt=chat_prompt)
    if tool_prompt is not None:
        session_handler.update_session_config(session_id, tool_prompt=tool_prompt)

    # Get updated config after changes
    updated_config = session_handler.get_session_config(session_id)

    # Dynamic prompts: chat prompt must be provided when chat is deployed
    static_prefix = updated_config.get("chat_prompt") or ""
    runtime_text = ""

    # Send ACK: session start / (re)config pinned
    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "start",
        "ok": True,
        "session_id": session_id,
        "now": sess_now_str,
        "assistant_gender": updated_config.get("chat_gender"),
        "personality": updated_config.get("chat_personality"),
        "chat_prompt": bool(updated_config.get("chat_prompt")),
    }))
    logger.info(f"handle_start: ack sent session_id={session_id}")

    # Process history and user utterance
    if "history_text" in msg:
        incoming_history = msg.get("history_text") or ""
        history_text = session_handler.set_history_text(session_id, incoming_history)
    else:
        history_text = session_handler.get_history_text(session_id)

    user_utt = msg["user_utterance"]

    # Trim user utterance using appropriate tokenizer based on deployment mode
    if DEPLOY_CHAT:
        user_utt = trim_text_to_token_limit_chat(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    elif DEPLOY_TOOL:
        user_utt = trim_text_to_token_limit_tool(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")

    # Choose execution based on deploy mode and concurrency flag
    async def _run_start():
        if DEPLOY_CHAT and DEPLOY_TOOL:
            if CONCURRENT_MODEL_CALL:
                logger.info(f"handle_start: concurrent execution session_id={session_id}")
                await run_concurrent_execution(ws, session_id, static_prefix, runtime_text, history_text, user_utt)
            else:
                logger.info(f"handle_start: sequential execution session_id={session_id}")
                await run_sequential_execution(ws, session_id, static_prefix, runtime_text, history_text, user_utt)
            return

        if DEPLOY_CHAT and not DEPLOY_TOOL:
            # Chat-only deployment: stream chat tokens and finalize
            logger.info(f"handle_start: chat-only streaming session_id={session_id}")
            final_text = await stream_chat_response(
                ws,
                run_chat_stream(
                    session_id,
                    static_prefix,
                    runtime_text,
                    history_text,
                    user_utt,
                ),
                session_id,
                user_utt,
            )
            logger.info(
                "handle_start: chat-only done session_id=%s chars=%s",
                session_id,
                len(final_text),
            )
            return

        if DEPLOY_TOOL and not DEPLOY_CHAT:
            # Tool-only deployment: run tool router, emit decision, and finalize
            logger.info(f"handle_start: tool-only routing session_id={session_id}")
            tool_res = await run_toolcall(session_id, user_utt, history_text, mark_active=False)
            raw_field, is_tool = parse_tool_result(tool_res)
            await ws.send_text(json.dumps({
                "type": "toolcall",
                "status": "yes" if is_tool else "no",
                "raw": raw_field,
            }))
            await ws.send_text(json.dumps({
                "type": "final",
                "normalized_text": ""
            }))
            await ws.send_text(json.dumps({"type": "done", "usage": {}}))
            logger.info(f"handle_start: tool-only done session_id={session_id} is_tool={is_tool}")
            return

    task = asyncio.create_task(_run_start())
    session_handler.session_tasks[session_id] = task


