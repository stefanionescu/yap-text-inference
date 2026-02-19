"""Map exceptions to telemetry error-type labels."""

from __future__ import annotations

from ..errors import RateLimitError, ValidationError, EngineNotReadyError, EngineShutdownError, StreamCancelledError

ERROR_TYPE_LABELS: tuple[tuple[type[BaseException], str], ...] = (
    (ValidationError, "validation"),
    (RateLimitError, "rate_limit"),
    (StreamCancelledError, "cancelled"),
    (EngineNotReadyError, "engine_not_ready"),
    (EngineShutdownError, "engine_shutdown"),
    (TimeoutError, "timeout"),
    (ConnectionError, "connection"),
)


def get_error_type(exc: BaseException) -> str:
    """Return the telemetry error type label for an exception."""

    for exception_type, label in ERROR_TYPE_LABELS:
        if isinstance(exc, exception_type):
            return label
    return "unknown"


__all__ = ["get_error_type"]
