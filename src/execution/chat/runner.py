"""High-level chat generation runner.

This module provides the main interface for streaming chat generation,
handling:

1. Sampling Parameter Resolution:
   - Merge default config with per-request overrides
   - Build engine-specific SamplingParams
   - Logit bias token ID mapping

2. Prompt Building:
   - Combine static prefix + runtime context + history + user message
   - Apply chat template via tokenizer

3. Stream Processing:
   - Delegate to ChatStreamController for buffering/timeout
   - Apply streaming sanitization (Unicode normalization, etc.)
   - Handle cancellation checks

The runner abstracts away engine differences - callers get a simple
async generator of text chunks regardless of vLLM vs TRT-LLM backend.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator

from ...engines import get_engine, create_sampling_params
from ...config import CHAT_MAX_OUT, STREAM_FLUSH_MS, CHAT_REQUEST_PRIORITY
from ...handlers.session import session_handler
from ...messages.sanitize import StreamingSanitizer
from ...config.sampling import (
    CHAT_TEMPERATURE,
    CHAT_TOP_P,
    CHAT_TOP_K,
    CHAT_MIN_P,
    CHAT_REPETITION_PENALTY,
    CHAT_PRESENCE_PENALTY,
    CHAT_FREQUENCY_PENALTY,
    INFERENCE_STOP,
    CHAT_LOGIT_BIAS,
)
from ...config.timeouts import GEN_TIMEOUT_S
from ...tokens.tokenizer import get_chat_tokenizer
from ...persona import build_chat_prompt_with_prefix
from .controller import ChatStreamConfig, ChatStreamController


# Cache for tokenized logit bias mapping
_logit_bias_cache: dict[int, float] | None = None


async def run_chat_generation(
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    request_id: str | None = None,
    *,
    sampling_overrides: dict[str, float | int | bool] | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat generation with optional micro-coalescing.
    
    This is the primary interface for generating chat responses. It:
    1. Resolves sampling parameters (defaults + overrides)
    2. Builds the full prompt with persona and history
    3. Streams generation through ChatStreamController
    4. Applies streaming sanitization (optional)
    
    Args:
        session_id: Session for request tracking and cancellation.
        static_prefix: Static persona system prompt.
        runtime_text: Runtime context (time, metadata).
        history_text: Conversation history.
        user_utt: User message to respond to.
        request_id: Optional request ID (auto-generated if None).
        sampling_overrides: Override default sampling parameters.
            Supported: temperature, top_p, top_k, min_p,
            repetition_penalty, presence_penalty, frequency_penalty,
            sanitize_output (bool).
            
    Yields:
        Text chunks as they're generated, sanitized and buffered.
    """
    req_id = request_id or f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, req_id)

    overrides = sampling_overrides or {}
    temperature = float(overrides.get("temperature", CHAT_TEMPERATURE))
    top_p = float(overrides.get("top_p", CHAT_TOP_P))
    top_k = int(overrides.get("top_k", CHAT_TOP_K))
    min_p = float(overrides.get("min_p", CHAT_MIN_P))
    repetition_penalty = float(overrides.get("repetition_penalty", CHAT_REPETITION_PENALTY))
    presence_penalty = float(overrides.get("presence_penalty", CHAT_PRESENCE_PENALTY))
    frequency_penalty = float(overrides.get("frequency_penalty", CHAT_FREQUENCY_PENALTY))
    sanitize_output = bool(overrides.get("sanitize_output", True))

    logit_bias = _get_logit_bias_map()

    # Use unified sampling params factory
    params = create_sampling_params(
        temperature=temperature,
        top_p=top_p,
        top_k=top_k,
        min_p=min_p,
        repetition_penalty=repetition_penalty,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        max_tokens=CHAT_MAX_OUT,
        stop=INFERENCE_STOP,
        logit_bias=logit_bias if logit_bias else None,
    )
    
    prompt = build_chat_prompt_with_prefix(static_prefix, runtime_text, history_text, user_utt)
    stream = ChatStreamController(
        ChatStreamConfig(
            session_id=session_id,
            request_id=req_id,
            prompt=prompt,
            sampling_params=params,
            engine_getter=get_engine,
            timeout_s=float(GEN_TIMEOUT_S),
            priority=CHAT_REQUEST_PRIORITY,
            flush_ms=float(STREAM_FLUSH_MS),
            cancel_check=lambda: session_handler.is_request_cancelled(session_id, req_id),
        )
    )

    sanitizer = StreamingSanitizer() if sanitize_output else None
    normal_completion = False
    try:
        async for chunk in stream:
            if sanitizer:
                clean = sanitizer.push(chunk)
                if clean:
                    yield clean
            else:
                yield chunk
        normal_completion = True
    finally:
        pass
    if normal_completion and sanitizer:
        tail = sanitizer.flush()
        if tail:
            yield tail


def _get_logit_bias_map() -> dict[int, float]:
    """Build logit bias map from text tokens to token IDs.
    
    The CHAT_LOGIT_BIAS config maps text strings to bias values.
    This function converts those to token ID -> bias mappings
    that the engine can use.
    
    The result is cached after first successful build.
    
    Returns:
        Dict mapping token IDs to logit bias values.
        Empty dict if no bias configured or tokenizer unavailable.
    """
    global _logit_bias_cache
    if _logit_bias_cache is not None:
        return _logit_bias_cache

    if not CHAT_LOGIT_BIAS:
        _logit_bias_cache = {}
        return _logit_bias_cache

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

    _logit_bias_cache = id_bias
    return id_bias


__all__ = ["run_chat_generation"]
