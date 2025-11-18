"""Chat streaming logic for real-time text generation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from vllm.sampling_params import SamplingParams

from ...engines import get_chat_engine
from ...persona import build_chat_prompt_with_prefix
from ...config import CHAT_MAX_OUT, STREAM_FLUSH_MS
from ...handlers.session_handler import session_handler
from ...config.sampling import (
    CHAT_TEMPERATURE,
    CHAT_TOP_P,
    CHAT_TOP_K,
    CHAT_MIN_P,
    CHAT_REPEAT_PENALTY,
    CHAT_STOP,
)
from ...config.timeouts import GEN_TIMEOUT_S
from .llm_stream import LLMStream, LLMStreamConfig


async def run_chat_stream(
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    request_id: str | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat generation with optional micro-coalescing."""
    req_id = request_id or f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, req_id)

    params = SamplingParams(
        temperature=CHAT_TEMPERATURE,
        top_p=CHAT_TOP_P,
        top_k=CHAT_TOP_K,
        min_p=CHAT_MIN_P,
        repetition_penalty=CHAT_REPEAT_PENALTY,
        max_tokens=CHAT_MAX_OUT,
        stop=CHAT_STOP,
    )
    prompt = build_chat_prompt_with_prefix(static_prefix, runtime_text, history_text, user_utt)
    stream = LLMStream(
        LLMStreamConfig(
            name="chat",
            session_id=session_id,
            request_id=req_id,
            prompt=prompt,
            sampling_params=params,
            engine_getter=get_chat_engine,
            timeout_s=float(GEN_TIMEOUT_S),
            priority=0,
            flush_ms=float(STREAM_FLUSH_MS),
            cancel_check=lambda: session_handler.is_request_cancelled(session_id, req_id),
        )
    )
    async for chunk in stream:
        yield chunk
