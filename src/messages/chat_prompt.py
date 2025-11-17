"""Handler to update chat prompt, gender, and personality mid-session.

Validates inputs, ensures at least gender or personality changes, sanitizes the
prompt, checks token limits, updates session state, and performs a one-time
warm to seed prefix caching with the new prompt + history.
"""

from __future__ import annotations

import json
import uuid
from typing import Dict, Any
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..handlers.session_handler import session_handler
from ..utils.validation import normalize_gender, normalize_personality
from ..utils.sanitize import sanitize_prompt
from ..tokens import (
    count_tokens_chat,
    trim_history_preserve_messages_chat,
)
from ..config import (
    HISTORY_MAX_TOKENS,
    CHAT_PROMPT_MAX_TOKENS,
)
from ..engines import get_chat_engine


async def handle_chat_prompt(ws: WebSocket, msg: Dict[str, Any], session_id: str) -> None:
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
    raw_gender = msg.get("assistant_gender")
    raw_personality = (msg.get("personality") or "").strip()
    raw_prompt = msg.get("chat_prompt") or msg.get("persona_text")
    history_text = session_handler.get_history_text(session_id)

    # Validate gender and personality first
    g = normalize_gender(raw_gender)
    if g is None:
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": False,
            "code": 400,
            "message": "assistant_gender must be 'female' or 'male'"
        }))
        return

    norm_personality = normalize_personality(raw_personality)
    if norm_personality is None:
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": False,
            "code": 400,
            "message": "personality must be letters-only and <= configured max length"
        }))
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
        chat_prompt = sanitize_prompt(raw_prompt)
    except Exception as e:
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": False,
            "code": 400,
            "message": str(e)
        }))
        return

    if count_tokens_chat(chat_prompt) > CHAT_PROMPT_MAX_TOKENS:
        await ws.send_text(json.dumps({
            "type": "ack",
            "for": "chat_prompt",
            "ok": False,
            "code": 413,
            "message": f"chat_prompt exceeds token limit ({CHAT_PROMPT_MAX_TOKENS})"
        }))
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
        "assistant_gender": g,
        "personality": norm_personality,
    }))


