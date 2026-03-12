"""High-level chat generation runner.

This module provides the main interface for streaming chat generation,
handling:

1. Sampling Parameter Resolution
2. Prompt validation / metrics
3. Stream Processing with optional sanitization
4. Cancellation checks
"""

from __future__ import annotations

import uuid
from typing import Any
from opentelemetry import trace
from src.engines.base import BaseEngine
from collections.abc import AsyncGenerator
from src.state.session import SessionState
from ...config.timeouts import GEN_TIMEOUT_S
from ...engines import create_sampling_params
from src.tokens.tokenizer import FastTokenizer
from src.telemetry.instruments import get_metrics
from ...messages.sanitize import StreamingSanitizer
from src.telemetry.phases import record_phase_latency
from .controller import ChatStreamConfig, ChatStreamController
from src.handlers.session.requests import is_request_cancelled
from ...config import CHAT_MAX_LEN, CHAT_MAX_OUT, STREAM_FLUSH_MS
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
    """Build logit bias map from text tokens to token IDs."""
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
    state: SessionState,
    prompt: str,
    *,
    engine: BaseEngine,
    chat_tokenizer: FastTokenizer,
    request_id: str | None = None,
    sampling_overrides: dict[str, float | int | bool] | None = None,
    prompt_token_count: int | None = None,
) -> AsyncGenerator[str, None]:
    """Stream chat generation with optional micro-coalescing."""
    req_id = request_id or f"chat-{uuid.uuid4()}"

    overrides = _resolve_sampling_overrides(sampling_overrides or {})
    params = _build_sampling_params(overrides, chat_tokenizer)

    record_phase_latency("prompt_build", 0.0)
    resolved_prompt_token_count = prompt_token_count
    if resolved_prompt_token_count is None:
        resolved_prompt_token_count = len(chat_tokenizer.encode_ids(prompt))
    if resolved_prompt_token_count > CHAT_MAX_LEN:
        raise ValueError(
            f"prompt exceeds exact context budget before engine call ({resolved_prompt_token_count} > {CHAT_MAX_LEN})"
        )
    m = get_metrics()
    m.prompt_tokens.record(resolved_prompt_token_count)
    m.prompt_tokens_total.add(resolved_prompt_token_count)
    span = trace.get_current_span()
    if span.is_recording():
        span.set_attribute("prompt_tokens", resolved_prompt_token_count)

    stream = ChatStreamController(
        ChatStreamConfig(
            session_id=state.session_id,
            request_id=req_id,
            prompt=prompt,
            sampling_params=params,
            engine=engine,
            timeout_s=float(GEN_TIMEOUT_S),
            flush_ms=float(STREAM_FLUSH_MS),
            cancel_check=lambda: is_request_cancelled(state, req_id),
            count_completion_tokens=chat_tokenizer.count,
        )
    )
    async for chunk in _stream_with_optional_sanitizer(stream, sanitize_output=bool(overrides["sanitize_output"])):
        yield chunk


__all__ = ["run_chat_generation"]
