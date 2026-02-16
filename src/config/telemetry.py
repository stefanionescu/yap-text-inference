"""Telemetry configuration: env vars, metric specs, span names, Sentry constants."""

import os

from ..errors import RateLimitError, ValidationError, EngineNotReadyError, EngineShutdownError, StreamCancelledError

# ---------------------------------------------------------------------------
# Sentry
# ---------------------------------------------------------------------------
SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
SENTRY_ENVIRONMENT: str = os.getenv("SENTRY_ENVIRONMENT", "production")
SENTRY_RELEASE: str = os.getenv("SENTRY_RELEASE", "")
SENTRY_SAMPLE_RATE: float = float(os.getenv("SENTRY_SAMPLE_RATE", "1.0"))

# ---------------------------------------------------------------------------
# Axiom / OTel
# ---------------------------------------------------------------------------
AXIOM_API_TOKEN: str = os.getenv("AXIOM_API_TOKEN", "")
AXIOM_DATASET: str = os.getenv("AXIOM_DATASET", "text-inference-api")
AXIOM_ENVIRONMENT: str = os.getenv("AXIOM_ENVIRONMENT", "production")
AXIOM_TRACES_ENDPOINT: str = os.getenv("AXIOM_TRACES_ENDPOINT", "https://api.axiom.co/v1/traces")
AXIOM_METRICS_ENDPOINT: str = os.getenv("AXIOM_METRICS_ENDPOINT", "https://api.axiom.co/v1/metrics")

# ---------------------------------------------------------------------------
# OTel tuning
# ---------------------------------------------------------------------------
OTEL_SERVICE_NAME: str = os.getenv("OTEL_SERVICE_NAME", "yap-text-inference-api")
OTEL_TRACES_EXPORT_INTERVAL_MS: int = int(os.getenv("OTEL_TRACES_EXPORT_INTERVAL_MS", "5000"))
OTEL_METRICS_EXPORT_INTERVAL_MS: int = int(os.getenv("OTEL_METRICS_EXPORT_INTERVAL_MS", "15000"))
OTEL_TRACES_BATCH_SIZE: int = int(os.getenv("OTEL_TRACES_BATCH_SIZE", "512"))

# ---------------------------------------------------------------------------
# Deployment
# ---------------------------------------------------------------------------
CLOUD_PLATFORM: str = os.getenv("CLOUD_PLATFORM", "")

# ---------------------------------------------------------------------------
# Metric spec tuples: (name, unit, description)
# ---------------------------------------------------------------------------

# Histograms
METRIC_TTFT = ("text_inference.ttft", "s", "Time to first token")
METRIC_REQUEST_LATENCY = ("text_inference.request_latency", "s", "End-to-end request latency")
METRIC_TOKEN_LATENCY = ("text_inference.token_latency", "s", "Inter-token arrival time")
METRIC_CONNECTION_DURATION = ("text_inference.connection_duration", "s", "WebSocket session duration")
METRIC_CONNECTION_SEMAPHORE_WAIT = ("text_inference.connection_semaphore_wait", "s", "Slot acquisition wait")
METRIC_PROMPT_TOKENS = ("text_inference.prompt_tokens", "{token}", "Input prompt token count")
METRIC_COMPLETION_TOKENS = ("text_inference.completion_tokens", "{token}", "Output completion token count")
METRIC_GENERATIONS_PER_SESSION = (
    "text_inference.generations_per_session",
    "{request}",
    "Requests per session",
)
METRIC_STARTUP_DURATION = ("text_inference.startup_duration", "s", "Server startup time")
METRIC_TOOL_CLASSIFICATION_LATENCY = (
    "text_inference.tool_classification_latency",
    "s",
    "Tool classifier inference time",
)

# Counters
METRIC_REQUESTS_TOTAL = ("text_inference.requests_total", "{request}", "Total requests")
METRIC_TOKENS_GENERATED_TOTAL = ("text_inference.tokens_generated_total", "{token}", "Total tokens generated")
METRIC_PROMPT_TOKENS_TOTAL = ("text_inference.prompt_tokens_total", "{token}", "Total prompt tokens processed")
METRIC_CONNECTIONS_REJECTED_TOTAL = (
    "text_inference.connections_rejected_total",
    "{connection}",
    "Rejected at capacity",
)
METRIC_SESSION_CHURN_TOTAL = ("text_inference.session_churn_total", "{session}", "Completed sessions")
METRIC_CANCELLATION_TOTAL = ("text_inference.cancellation_total", "{request}", "Client cancellations")
METRIC_ERRORS_TOTAL = ("text_inference.errors_total", "{error}", "Unhandled errors")
METRIC_TIMEOUT_DISCONNECTS_TOTAL = (
    "text_inference.timeout_disconnects_total",
    "{connection}",
    "Idle timeout disconnects",
)
METRIC_RATE_LIMIT_VIOLATIONS_TOTAL = (
    "text_inference.rate_limit_violations_total",
    "{violation}",
    "Rate limit hits",
)
METRIC_TOOL_CLASSIFICATIONS_TOTAL = (
    "text_inference.tool_classifications_total",
    "{classification}",
    "Tool classifier calls",
)
METRIC_CACHE_RESETS_TOTAL = ("text_inference.cache_resets_total", "{reset}", "vLLM cache resets")

# UpDown counters
METRIC_ACTIVE_CONNECTIONS = ("text_inference.active_connections", "{connection}", "Current WebSocket connections")
METRIC_ACTIVE_GENERATIONS = ("text_inference.active_generations", "{generation}", "Currently running generations")

# GPU observables
METRIC_GPU_MEMORY_USED = ("text_inference.gpu.memory_used", "By", "GPU memory in use")
METRIC_GPU_MEMORY_FREE = ("text_inference.gpu.memory_free", "By", "GPU memory available")
METRIC_GPU_MEMORY_TOTAL = ("text_inference.gpu.memory_total", "By", "Total GPU memory")
METRIC_GPU_UTILIZATION = ("text_inference.gpu.utilization", "%", "GPU compute utilization")

# ---------------------------------------------------------------------------
# Span names
# ---------------------------------------------------------------------------
SPAN_SESSION = "text_inference.session"
SPAN_REQUEST = "text_inference.request"
SPAN_GENERATION = "text_inference.generation"

# ---------------------------------------------------------------------------
# Sentry constants
# ---------------------------------------------------------------------------
SENTRY_RATE_LIMIT_S: float = 10.0
SENTRY_TAG_SESSION_ID = "session_id"
SENTRY_TAG_REQUEST_ID = "request_id"
SENTRY_TAG_CLIENT_ID = "client_id"

# ---------------------------------------------------------------------------
# Error classification mapping
# ---------------------------------------------------------------------------
_ERROR_CATEGORIES: tuple[tuple[type, str], ...] = (
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
    for cls, label in _ERROR_CATEGORIES:
        if isinstance(exc, cls):
            return label
    return "unknown"


__all__ = [
    # Sentry env
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE",
    "SENTRY_SAMPLE_RATE",
    # Axiom / OTel env
    "AXIOM_API_TOKEN",
    "AXIOM_DATASET",
    "AXIOM_ENVIRONMENT",
    "AXIOM_TRACES_ENDPOINT",
    "AXIOM_METRICS_ENDPOINT",
    # OTel tuning
    "OTEL_SERVICE_NAME",
    "OTEL_TRACES_EXPORT_INTERVAL_MS",
    "OTEL_METRICS_EXPORT_INTERVAL_MS",
    "OTEL_TRACES_BATCH_SIZE",
    # Deployment
    "CLOUD_PLATFORM",
    # Histograms
    "METRIC_TTFT",
    "METRIC_REQUEST_LATENCY",
    "METRIC_TOKEN_LATENCY",
    "METRIC_CONNECTION_DURATION",
    "METRIC_CONNECTION_SEMAPHORE_WAIT",
    "METRIC_PROMPT_TOKENS",
    "METRIC_COMPLETION_TOKENS",
    "METRIC_GENERATIONS_PER_SESSION",
    "METRIC_STARTUP_DURATION",
    "METRIC_TOOL_CLASSIFICATION_LATENCY",
    # Counters
    "METRIC_REQUESTS_TOTAL",
    "METRIC_TOKENS_GENERATED_TOTAL",
    "METRIC_PROMPT_TOKENS_TOTAL",
    "METRIC_CONNECTIONS_REJECTED_TOTAL",
    "METRIC_SESSION_CHURN_TOTAL",
    "METRIC_CANCELLATION_TOTAL",
    "METRIC_ERRORS_TOTAL",
    "METRIC_TIMEOUT_DISCONNECTS_TOTAL",
    "METRIC_RATE_LIMIT_VIOLATIONS_TOTAL",
    "METRIC_TOOL_CLASSIFICATIONS_TOTAL",
    "METRIC_CACHE_RESETS_TOTAL",
    # UpDown counters
    "METRIC_ACTIVE_CONNECTIONS",
    "METRIC_ACTIVE_GENERATIONS",
    # GPU observables
    "METRIC_GPU_MEMORY_USED",
    "METRIC_GPU_MEMORY_FREE",
    "METRIC_GPU_MEMORY_TOTAL",
    "METRIC_GPU_UTILIZATION",
    # Span names
    "SPAN_SESSION",
    "SPAN_REQUEST",
    "SPAN_GENERATION",
    # Sentry constants
    "SENTRY_RATE_LIMIT_S",
    "SENTRY_TAG_SESSION_ID",
    "SENTRY_TAG_REQUEST_ID",
    "SENTRY_TAG_CLIENT_ID",
    # Error classification
    "_ERROR_CATEGORIES",
    "classify_error",
]
