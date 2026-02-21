"""MetricInstruments registry — typed accessors for all OTel instruments."""

from __future__ import annotations

import logging
from opentelemetry import metrics
from .gpu import register_gpu_observables
from ..config.telemetry import (
    METRIC_TTFT,
    OTEL_SERVICE_NAME,
    METRIC_ERRORS_TOTAL,
    METRIC_PROMPT_TOKENS,
    METRIC_TOKEN_LATENCY,
    METRIC_REQUESTS_TOTAL,
    METRIC_REQUEST_LATENCY,
    METRIC_STARTUP_DURATION,
    METRIC_COMPLETION_TOKENS,
    METRIC_ACTIVE_CONNECTIONS,
    METRIC_ACTIVE_GENERATIONS,
    METRIC_CACHE_RESETS_TOTAL,
    METRIC_CANCELLATION_TOTAL,
    METRIC_CONNECTION_DURATION,
    METRIC_PROMPT_TOKENS_TOTAL,
    METRIC_SESSION_CHURN_TOTAL,
    METRIC_TOKENS_GENERATED_TOTAL,
    METRIC_GENERATIONS_PER_SESSION,
    METRIC_CONNECTION_SEMAPHORE_WAIT,
    METRIC_TIMEOUT_DISCONNECTS_TOTAL,
    METRIC_CONNECTIONS_REJECTED_TOTAL,
    METRIC_TOOL_CLASSIFICATIONS_TOTAL,
    METRIC_RATE_LIMIT_VIOLATIONS_TOTAL,
    METRIC_TOOL_CLASSIFICATION_LATENCY,
)

logger = logging.getLogger(__name__)


def _histogram(meter: metrics.Meter, spec: tuple[str, str, str]) -> metrics.Histogram:
    name, unit, desc = spec
    return meter.create_histogram(name, unit=unit, description=desc)


def _counter(meter: metrics.Meter, spec: tuple[str, str, str]) -> metrics.Counter:
    name, unit, desc = spec
    return meter.create_counter(name, unit=unit, description=desc)


def _updown(meter: metrics.Meter, spec: tuple[str, str, str]) -> metrics.UpDownCounter:
    name, unit, desc = spec
    return meter.create_up_down_counter(name, unit=unit, description=desc)


class MetricInstruments:
    """Holds all OTel metric instruments created from config specs."""

    __slots__ = (
        "ttft",
        "request_latency",
        "token_latency",
        "connection_duration",
        "connection_semaphore_wait",
        "prompt_tokens",
        "completion_tokens",
        "generations_per_session",
        "startup_duration",
        "tool_classification_latency",
        "requests_total",
        "tokens_generated_total",
        "prompt_tokens_total",
        "connections_rejected_total",
        "session_churn_total",
        "cancellation_total",
        "errors_total",
        "timeout_disconnects_total",
        "rate_limit_violations_total",
        "tool_classifications_total",
        "cache_resets_total",
        "active_connections",
        "active_generations",
    )

    def __init__(self, meter: metrics.Meter) -> None:
        # Histograms
        self.ttft = _histogram(meter, METRIC_TTFT)
        self.request_latency = _histogram(meter, METRIC_REQUEST_LATENCY)
        self.token_latency = _histogram(meter, METRIC_TOKEN_LATENCY)
        self.connection_duration = _histogram(meter, METRIC_CONNECTION_DURATION)
        self.connection_semaphore_wait = _histogram(meter, METRIC_CONNECTION_SEMAPHORE_WAIT)
        self.prompt_tokens = _histogram(meter, METRIC_PROMPT_TOKENS)
        self.completion_tokens = _histogram(meter, METRIC_COMPLETION_TOKENS)
        self.generations_per_session = _histogram(meter, METRIC_GENERATIONS_PER_SESSION)
        self.startup_duration = _histogram(meter, METRIC_STARTUP_DURATION)
        self.tool_classification_latency = _histogram(meter, METRIC_TOOL_CLASSIFICATION_LATENCY)
        # Counters
        self.requests_total = _counter(meter, METRIC_REQUESTS_TOTAL)
        self.tokens_generated_total = _counter(meter, METRIC_TOKENS_GENERATED_TOTAL)
        self.prompt_tokens_total = _counter(meter, METRIC_PROMPT_TOKENS_TOTAL)
        self.connections_rejected_total = _counter(meter, METRIC_CONNECTIONS_REJECTED_TOTAL)
        self.session_churn_total = _counter(meter, METRIC_SESSION_CHURN_TOTAL)
        self.cancellation_total = _counter(meter, METRIC_CANCELLATION_TOTAL)
        self.errors_total = _counter(meter, METRIC_ERRORS_TOTAL)
        self.timeout_disconnects_total = _counter(meter, METRIC_TIMEOUT_DISCONNECTS_TOTAL)
        self.rate_limit_violations_total = _counter(meter, METRIC_RATE_LIMIT_VIOLATIONS_TOTAL)
        self.tool_classifications_total = _counter(meter, METRIC_TOOL_CLASSIFICATIONS_TOTAL)
        self.cache_resets_total = _counter(meter, METRIC_CACHE_RESETS_TOTAL)
        # UpDown counters
        self.active_connections = _updown(meter, METRIC_ACTIVE_CONNECTIONS)
        self.active_generations = _updown(meter, METRIC_ACTIVE_GENERATIONS)


_metrics: MetricInstruments | None = None


def get_metrics() -> MetricInstruments:
    """Return the global MetricInstruments (no-op meter if OTel not initialized)."""
    global _metrics  # noqa: PLW0603
    if _metrics is None:
        meter = metrics.get_meter(OTEL_SERVICE_NAME)
        _metrics = MetricInstruments(meter)
    return _metrics


def initialize_metrics() -> None:
    """Create MetricInstruments from the global meter and register GPU observables."""
    global _metrics  # noqa: PLW0603
    meter = metrics.get_meter(OTEL_SERVICE_NAME)
    _metrics = MetricInstruments(meter)
    register_gpu_observables(meter)
    logger.info("Telemetry metrics initialized")


__all__ = ["MetricInstruments", "get_metrics", "initialize_metrics"]
