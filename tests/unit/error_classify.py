"""Unit tests for exception-to-metric classification."""

from __future__ import annotations

from src.errors import (
    RateLimitError,
    ValidationError,
    EngineNotReadyError,
    EngineShutdownError,
    StreamCancelledError,
    classify_error,
)


def test_classify_error_known_categories() -> None:
    assert classify_error(ValidationError("invalid_payload", "bad payload")) == "validation"
    assert classify_error(RateLimitError(retry_in=1.0, limit=10, window_seconds=1.0)) == "rate_limit"
    assert classify_error(StreamCancelledError()) == "cancelled"
    assert classify_error(EngineNotReadyError()) == "engine_not_ready"
    assert classify_error(EngineShutdownError()) == "engine_shutdown"
    assert classify_error(TimeoutError("deadline exceeded")) == "timeout"
    assert classify_error(ConnectionError("socket closed")) == "connection"


def test_classify_error_defaults_to_unknown() -> None:
    assert classify_error(RuntimeError("boom")) == "unknown"
