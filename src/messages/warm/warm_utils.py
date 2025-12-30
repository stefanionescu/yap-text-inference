"""Shared helpers for warm_persona/history handlers."""

from __future__ import annotations

import json
import uuid

from fastapi import WebSocket

from ...engines import get_engine, create_sampling_params
from ..sanitize.prompt_sanitizer import sanitize_prompt
from ...handlers.websocket.helpers import safe_send_json

_WARM_PARAMS = None


def _get_warm_params():
    """Lazy initialization of warm params to avoid import-time engine detection."""
    global _WARM_PARAMS
    if _WARM_PARAMS is None:
        _WARM_PARAMS = create_sampling_params(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    return _WARM_PARAMS


async def warm_chat_segment(
    ws: WebSocket,
    *,
    prompt: str,
    segment: str,
    byte_count: int,
) -> None:
    """Generic warming helper for persona/history segments."""
    req_id = f"warm-{segment}-{uuid.uuid4()}"
    engine = await get_engine()
    async for _ in engine.generate_stream(
        prompt=prompt,
        sampling_params=_get_warm_params(),
        request_id=req_id,
    ):
        break

    await safe_send_json(ws, {
        "type": "warmed",
        "segment": segment,
        "bytes": byte_count,
    })


def sanitize_optional_prompt(raw: str | None) -> str:
    """Sanitize optional persona/runtime fields; empty when missing."""
    if raw is None:
        return ""
    text = raw.strip()
    if not text:
        return ""
    return sanitize_prompt(text)


__all__ = ["warm_chat_segment", "sanitize_optional_prompt"]
