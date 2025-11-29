"""Shared helpers for warm_persona/history handlers."""

from __future__ import annotations

import json
import uuid

from vllm.sampling_params import SamplingParams
from fastapi import WebSocket

from ...config import WARM_REQUEST_PRIORITY
from ...engines import get_chat_engine
from ...tokens.prompt_cache import CompiledPrompt

_WARM_PARAMS = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])


async def warm_chat_segment(
    ws: WebSocket,
    *,
    compiled_prompt: CompiledPrompt,
    segment: str,
    byte_count: int,
) -> None:
    """Generic warming helper for persona/history segments."""
    req_id = f"warm-{segment}-{uuid.uuid4()}"
    stream = (await get_chat_engine()).generate(
        prompt=None,
        prompt_token_ids=compiled_prompt.token_ids,
        sampling_params=_WARM_PARAMS,
        request_id=req_id,
        priority=WARM_REQUEST_PRIORITY,
        use_prefix_cache=True,
    )
    async for _ in stream:
        break

    await ws.send_text(json.dumps({
        "type": "warmed",
        "segment": segment,
        "bytes": byte_count,
    }))


__all__ = ["warm_chat_segment"]

