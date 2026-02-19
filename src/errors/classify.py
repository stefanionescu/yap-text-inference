"""Exception classification helpers for metrics and telemetry labels."""

from __future__ import annotations

from .limits import RateLimitError
from .validation import ValidationError
from .stream import StreamCancelledError
from .engine import EngineNotReadyError, EngineShutdownError

ERROR_CATEGORIES: tuple[tuple[type[BaseException], str], ...] = (
    (ValidationError, "validation"),
    (RateLimitError, "rate_limit"),
    (StreamCancelledError, "cancelled"),
    (EngineNotReadyError, "engine_not_ready"),
    (EngineShutdownError, "engine_shutdown"),
    (TimeoutError, "timeout"),
    (ConnectionError, "connection"),
)


def classify_error(exc: BaseException) -> str:
    """Map an exception to a metric-friendly category label."""

    for cls, label in ERROR_CATEGORIES:
        if isinstance(exc, cls):
            return label
    return "unknown"


__all__ = ["ERROR_CATEGORIES", "classify_error"]
