"""Unit tests for telemetry error type mapping."""

from __future__ import annotations

from src.telemetry.errors import get_error_type
from src.errors import RateLimitError, ValidationError, EngineNotReadyError, EngineShutdownError, StreamCancelledError


def test_get_error_type_known_categories() -> None:
    assert get_error_type(ValidationError("invalid_payload", "bad payload")) == "validation"
    assert get_error_type(RateLimitError(retry_in=1.0, limit=10, window_seconds=1.0)) == "rate_limit"
    assert get_error_type(StreamCancelledError()) == "cancelled"
    assert get_error_type(EngineNotReadyError()) == "engine_not_ready"
    assert get_error_type(EngineShutdownError()) == "engine_shutdown"
    assert get_error_type(TimeoutError("deadline exceeded")) == "timeout"
    assert get_error_type(ConnectionError("socket closed")) == "connection"


def test_get_error_type_defaults_to_unknown() -> None:
    assert get_error_type(RuntimeError("boom")) == "unknown"
