"""Shared helpers for warm_persona/history handlers."""

from __future__ import annotations

import json
import uuid

from vllm.sampling_params import SamplingParams
from fastapi import WebSocket

from ...engines import get_chat_engine

_WARM_PARAMS = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])


async def warm_chat_segment(
    ws: WebSocket,
    *,
    prompt: str,
    segment: str,
    byte_count: int,
) -> None:
    """Generic warming helper for persona/history segments."""
    req_id = f"warm-{segment}-{uuid.uuid4()}"
    stream = (await get_chat_engine()).generate(
        prompt=prompt,
        sampling_params=_WARM_PARAMS,
        request_id=req_id,
        priority=1,
    )
    async for _ in stream:
        break

    await ws.send_text(json.dumps({
        "type": "warmed",
        "segment": segment,
        "bytes": byte_count,
    }))


__all__ = ["warm_chat_segment"]

