"""Chat streaming logic for real-time text generation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from vllm.sampling_params import SamplingParams

from ...engines import get_chat_engine
from ...persona import build_chat_prompt_with_prefix
from ...config import CHAT_MAX_OUT, STREAM_FLUSH_MS
from ...handlers.session_handler import session_handler
from ...utils.sanitize import StreamingSanitizer
from functools import lru_cache

from ...config.sampling import (
    CHAT_TEMPERATURE,
    CHAT_TOP_P,
    CHAT_TOP_K,
    CHAT_MIN_P,
    CHAT_REPEAT_PENALTY,
    CHAT_PRESENCE_PENALTY,
    CHAT_FREQUENCY_PENALTY,
    CHAT_LENGTH_PENALTY,
    CHAT_STOP,
    CHAT_LOGIT_BIAS,
)
from ...config.timeouts import GEN_TIMEOUT_S
from .llm_stream import LLMStream, LLMStreamConfig
from ...tokens.tokenizer import get_chat_tokenizer


async def run_chat_stream(
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    request_id: str | None = None,
    *,
    sampling_overrides: dict[str, float | int] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat generation with optional micro-coalescing."""
    req_id = request_id or f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, req_id)

    overrides = sampling_overrides or {}
    temperature = float(overrides.get("temperature", CHAT_TEMPERATURE))
    top_p = float(overrides.get("top_p", CHAT_TOP_P))
    top_k = int(overrides.get("top_k", CHAT_TOP_K))
    min_p = float(overrides.get("min_p", CHAT_MIN_P))
    repeat_penalty = float(overrides.get("repeat_penalty", CHAT_REPEAT_PENALTY))
    presence_penalty = float(overrides.get("presence_penalty", CHAT_PRESENCE_PENALTY))
    frequency_penalty = float(overrides.get("frequency_penalty", CHAT_FREQUENCY_PENALTY))
    length_penalty = float(overrides.get("length_penalty", CHAT_LENGTH_PENALTY))

    logit_bias = _get_logit_bias_map()

    params = SamplingParams(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        repetition_penalty=repeat_penalty,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        length_penalty=length_penalty,
        logit_bias=logit_bias if logit_bias else None,
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

    sanitizer = StreamingSanitizer()
    normal_completion = False
    try:
        async for chunk in stream:
            clean = sanitizer.push(chunk)
            if clean:
                yield clean
        normal_completion = True
    finally:
        pass  # Cleanup if needed, but don't return or yield here
    if normal_completion:
        tail = sanitizer.flush()
        if tail:
            yield tail


@lru_cache(maxsize=1)
def _get_logit_bias_map() -> dict[int, float]:
    if not CHAT_LOGIT_BIAS:
        return {}
    try:
        tokenizer = get_chat_tokenizer()
    except Exception:
        return {}

    id_bias: dict[int, float] = {}
    for text, bias in CHAT_LOGIT_BIAS.items():
        ids = tokenizer.encode_ids(text)
        if not ids:
            continue
        for token_id in ids:
            current = id_bias.get(token_id)
            value = float(bias)
            if current is None or value < current:
                id_bias[token_id] = value
    return id_bias
