"""Public telemetry API — re-exports for convenience."""

from .sentry import capture_error, add_breadcrumb
from .setup import init_telemetry, shutdown_telemetry
from .instruments import get_metrics, initialize_metrics
from .traces import request_span, session_span, generation_span

__all__ = [
    "init_telemetry",
    "shutdown_telemetry",
    "capture_error",
    "add_breadcrumb",
    "get_metrics",
    "initialize_metrics",
    "session_span",
    "request_span",
    "generation_span",
]
