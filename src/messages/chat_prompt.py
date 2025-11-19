"""Handler to update chat prompt, gender, and personality mid-session.

Validates inputs, ensures at least gender or personality changes, sanitizes the
prompt, checks token limits, updates session state, and performs a one-time
warm to seed prefix caching with the new prompt + history.
"""

from __future__ import annotations

import json
import math
import uuid
from typing import Any
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..handlers.session_handler import session_handler
from ..config import DEPLOY_CHAT
from ..tokens import (
    count_tokens_chat,
    trim_history_preserve_messages_chat,
)
from ..config import (
    HISTORY_MAX_TOKENS,
    CHAT_PROMPT_MAX_TOKENS,
    CHAT_PROMPT_UPDATE_MAX_PER_WINDOW,
    CHAT_PROMPT_UPDATE_WINDOW_SECONDS,
)
from ..engines import get_chat_engine
from .validators import (
    ValidationError,
    require_prompt,
    sanitize_prompt_with_limit,
    validate_required_gender,
    validate_required_personality,
)

_ERROR_CODE_MAP = {
    "chat_prompt_too_long": 413,
    "chat_prompt_update_rate_limited": 429,
}


async def _send_ack_error(ws: WebSocket, err: ValidationError) -> None:
    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "chat_prompt",
        "ok": False,
        "code": _ERROR_CODE_MAP.get(err.error_code, 400),
        "message": err.message,
    }))


async def handle_chat_prompt(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    if not DEPLOY_CHAT:
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": False,
            "code": 400,
            "message": "chat_prompt requires chat model deployment"
        }))
        return
    
    cfg = session_handler.get_session_config(session_id)
    if not cfg:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session; send 'start' first"}))
        return

    # Disallow tool prompt updates here
    if msg.get("tool_prompt"):
        await ws.send_text(json.dumps({
            "type": "error",
            "error_code": "tool_prompt_update_not_allowed",
            "message": "tool_prompt cannot be updated mid-session"
        }))
        return

    # Required fields
    raw_gender = msg.get("gender")
    raw_personality = msg.get("personality")
    raw_prompt = msg.get("chat_prompt") or msg.get("persona_text")
    history_text = session_handler.get_history_text(session_id)

    # Validate gender and personality first
    try:
        g = validate_required_gender(raw_gender)
        norm_personality = validate_required_personality(raw_personality)
    except ValidationError as err:
        await _send_ack_error(ws, err)
        return

    # Must change at least one of gender or personality
    if (cfg.get("chat_gender") == g) and (cfg.get("chat_personality") == norm_personality):
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": True,
            "code": 204,
            "message": "no change"
        }))
        return

    # Sanitize and length-check prompt
    try:
        base_prompt = require_prompt(
            raw_prompt,
            error_code="invalid_chat_prompt",
            message="chat_prompt is required",
        )
        chat_prompt = sanitize_prompt_with_limit(
            base_prompt,
            field_label="chat_prompt",
            invalid_error_code="invalid_chat_prompt",
            too_long_error_code="chat_prompt_too_long",
            max_tokens=CHAT_PROMPT_MAX_TOKENS,
            count_tokens_fn=count_tokens_chat,
        )
    except ValidationError as err:
        await _send_ack_error(ws, err)
        return

    # Rolling-window rate limit
    retry_seconds = session_handler.consume_chat_prompt_update(
        session_id,
        limit=CHAT_PROMPT_UPDATE_MAX_PER_WINDOW,
        window_seconds=CHAT_PROMPT_UPDATE_WINDOW_SECONDS,
    )
    if retry_seconds > 0:
        retry_in = int(max(1, math.ceil(retry_seconds)))
        window_desc = int(CHAT_PROMPT_UPDATE_WINDOW_SECONDS)
        message = (
            f"chat_prompt can be updated at most {CHAT_PROMPT_UPDATE_MAX_PER_WINDOW} times "
            f"every {window_desc} seconds; retry in {retry_in} seconds"
        )
        await _send_ack_error(ws, ValidationError("chat_prompt_update_rate_limited", message))
        return

    # Update session state
    session_handler.update_session_config(
        session_id,
        chat_gender=g,
        chat_personality=norm_personality,
        chat_prompt=chat_prompt,
    )
    # Trim history (chat tokenizer) and warm the new prefix (prompt + history)
    if count_tokens_chat(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages_chat(history_text, HISTORY_MAX_TOKENS)
        session_handler.set_history_text(session_id, history_text)

    warm_prompt = (
        f"<|persona|>\n{chat_prompt.strip()}\n"
        f"<|history|>\n{history_text.strip()}\n"
        f"<|assistant|>\n"
    )
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    req_id = f"warm-update-{uuid.uuid4()}"

    stream = (await get_chat_engine()).generate(
        prompt=warm_prompt,
        sampling_params=params,
        request_id=req_id,
        priority=1,
    )
    async for _ in stream:
        break

    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "chat_prompt",
        "ok": True,
        "code": 200,
        "message": "updated",
        "gender": g,
        "personality": norm_personality,
    }))


