"""Span context managers for session, request, and generation tracing."""

from __future__ import annotations

from typing import Any
from opentelemetry import trace
from collections.abc import Iterator
from contextlib import contextmanager
from ..config.telemetry import SPAN_REQUEST, SPAN_SESSION, SPAN_GENERATION, OTEL_SERVICE_NAME


def _tracer() -> trace.Tracer:
    return trace.get_tracer(OTEL_SERVICE_NAME)


@contextmanager
def session_span(*, session_id: str, client_id: str) -> Iterator[trace.Span]:
    """Outermost span wrapping the entire WebSocket connection."""
    with _tracer().start_as_current_span(
        SPAN_SESSION,
        attributes={"session.id": session_id, "client.id": client_id},
    ) as span:
        yield span


@contextmanager
def request_span(
    *,
    request_id: str,
    model: str = "",
    prompt_tokens: int = 0,
    temperature: float = 0.0,
) -> Iterator[trace.Span]:
    """Per-message/turn span."""
    attrs: dict[str, Any] = {"request.id": request_id}
    if model:
        attrs["model"] = model
    if prompt_tokens:
        attrs["prompt_tokens"] = prompt_tokens
    if temperature:
        attrs["temperature"] = temperature
    with _tracer().start_as_current_span(SPAN_REQUEST, attributes=attrs) as span:
        yield span


@contextmanager
def generation_span(
    *,
    engine_type: str = "",
    completion_tokens: int = 0,
    finish_reason: str = "",
) -> Iterator[trace.Span]:
    """Engine generation call span."""
    attrs: dict[str, Any] = {}
    if engine_type:
        attrs["engine.type"] = engine_type
    with _tracer().start_as_current_span(SPAN_GENERATION, attributes=attrs) as span:
        yield span
        if completion_tokens:
            span.set_attribute("completion_tokens", completion_tokens)
        if finish_reason:
            span.set_attribute("finish_reason", finish_reason)


__all__ = ["session_span", "request_span", "generation_span"]
