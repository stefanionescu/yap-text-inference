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
from typing import Any
from src.engines.base import BaseEngine
from collections.abc import AsyncGenerator
from ...config.timeouts import GEN_TIMEOUT_S
from ...engines import create_sampling_params
from src.tokens.tokenizer import FastTokenizer
from src.telemetry.instruments import get_metrics
from ...config import CHAT_MAX_OUT, STREAM_FLUSH_MS
from ...messages.sanitize import StreamingSanitizer
from src.handlers.session.manager import SessionHandler
from ...messages.chat import build_chat_prompt_with_prefix
from .controller import ChatStreamConfig, ChatStreamController
from ...config.sampling import (
    CHAT_MIN_P,
    CHAT_TOP_K,
    CHAT_TOP_P,
    INFERENCE_STOP,
    CHAT_LOGIT_BIAS,
    CHAT_TEMPERATURE,
    CHAT_PRESENCE_PENALTY,
    CHAT_FREQUENCY_PENALTY,
    CHAT_REPETITION_PENALTY,
)


def _resolve_sampling_overrides(
    overrides: dict[str, float | int | bool],
) -> dict[str, float | int | bool]:
    return {
        "temperature": float(overrides.get("temperature", CHAT_TEMPERATURE)),
        "top_p": float(overrides.get("top_p", CHAT_TOP_P)),
        "top_k": int(overrides.get("top_k", CHAT_TOP_K)),
        "min_p": float(overrides.get("min_p", CHAT_MIN_P)),
        "repetition_penalty": float(overrides.get("repetition_penalty", CHAT_REPETITION_PENALTY)),
        "presence_penalty": float(overrides.get("presence_penalty", CHAT_PRESENCE_PENALTY)),
        "frequency_penalty": float(overrides.get("frequency_penalty", CHAT_FREQUENCY_PENALTY)),
        "sanitize_output": bool(overrides.get("sanitize_output", True)),
    }


def _build_logit_bias_map(chat_tokenizer: FastTokenizer) -> dict[int, float]:
    """Build logit bias map from text tokens to token IDs.

    The CHAT_LOGIT_BIAS config maps text strings to bias values.
    This function converts those to token ID -> bias mappings
    that the engine can use.

    Uses @functools.cache for memoization - computed once on first call.

    Returns:
        Dict mapping token IDs to logit bias values.
        Empty dict if no bias configured or tokenizer unavailable.
    """
    if not CHAT_LOGIT_BIAS:
        return {}

    id_bias: dict[int, float] = {}
    for text, bias in CHAT_LOGIT_BIAS.items():
        ids = chat_tokenizer.encode_ids(text)
        if not ids:
            continue
        for token_id in ids:
            current = id_bias.get(token_id)
            value = float(bias)
            if current is None or value < current:
                id_bias[token_id] = value

    return id_bias


def _build_sampling_params(overrides: dict[str, float | int | bool], chat_tokenizer: FastTokenizer) -> Any:
    logit_bias = _build_logit_bias_map(chat_tokenizer)
    return create_sampling_params(
        temperature=float(overrides["temperature"]),
        top_p=float(overrides["top_p"]),
        top_k=int(overrides["top_k"]),
        min_p=float(overrides["min_p"]),
        repetition_penalty=float(overrides["repetition_penalty"]),
        presence_penalty=float(overrides["presence_penalty"]),
        frequency_penalty=float(overrides["frequency_penalty"]),
        max_tokens=CHAT_MAX_OUT,
        stop=INFERENCE_STOP,
        logit_bias=logit_bias if logit_bias else None,
    )


def _build_stream(
    *,
    session_id: str,
    request_id: str,
    prompt: str,
    sampling_params: Any,
    engine: BaseEngine,
    session_handler: SessionHandler,
) -> ChatStreamController:
    return ChatStreamController(
        ChatStreamConfig(
            session_id=session_id,
            request_id=request_id,
            prompt=prompt,
            sampling_params=sampling_params,
            engine=engine,
            timeout_s=float(GEN_TIMEOUT_S),
            flush_ms=float(STREAM_FLUSH_MS),
            cancel_check=lambda: session_handler.is_request_cancelled(session_id, request_id),
        )
    )


async def _stream_with_optional_sanitizer(
    stream: ChatStreamController,
    sanitize_output: bool,
) -> AsyncGenerator[str, None]:
    sanitizer = StreamingSanitizer() if sanitize_output else None
    completed = False
    async for chunk in stream:
        if sanitizer is None:
            yield chunk
            continue
        clean = sanitizer.push(chunk)
        if clean:
            yield clean
    completed = True
    if completed and sanitizer is not None:
        tail = sanitizer.flush()
        if tail:
            yield tail


async def run_chat_generation(
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
    *,
    engine: BaseEngine,
    session_handler: SessionHandler,
    chat_tokenizer: FastTokenizer,
    request_id: str | None = None,
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

    overrides = _resolve_sampling_overrides(sampling_overrides or {})
    params = _build_sampling_params(overrides, chat_tokenizer)

    prompt = build_chat_prompt_with_prefix(
        static_prefix,
        runtime_text,
        history_text,
        user_utt,
        chat_tokenizer,
    )
    prompt_token_count = len(chat_tokenizer.encode_ids(prompt))
    m = get_metrics()
    m.prompt_tokens.record(prompt_token_count)
    m.prompt_tokens_total.add(prompt_token_count)

    stream = _build_stream(
        session_id=session_id,
        request_id=req_id,
        prompt=prompt,
        sampling_params=params,
        engine=engine,
        session_handler=session_handler,
    )
    async for chunk in _stream_with_optional_sanitizer(stream, sanitize_output=bool(overrides["sanitize_output"])):
        yield chunk


__all__ = ["run_chat_generation"]
