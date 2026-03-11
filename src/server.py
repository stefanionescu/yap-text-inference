"""Main FastAPI server for the Yap Text Inference stack.

This module initializes and runs the inference server, supporting both vLLM and
TensorRT-LLM backends. It provides:

- An internal-only health endpoint (/healthz)
- A WebSocket endpoint for chat interactions (/ws)
- Automatic engine warm-up on startup
- Periodic cache reset for vLLM (prevents KV cache fragmentation)
- Graceful shutdown with engine cleanup

Server Lifecycle:
    1. On startup: Preload configured engines (chat and/or tool)
    2. Accept WebSocket connections on /ws
    3. Route messages through handlers (start, message, cancel, etc.)
    4. Periodically reset vLLM caches (timer-based or on long session end)
    5. On shutdown: Clean up engine resources

Important:
    Multiprocessing start method MUST be set to 'spawn' before any CUDA imports.
    This is critical for vLLM's worker processes to initialize correctly.

Example:
    Run directly with uvicorn:
        $ uvicorn src.server:app --host 0.0.0.0 --port 8000

    Or programmatically:
        from src.server import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from __future__ import annotations

import time
import logging
import contextlib
import multiprocessing
from collections.abc import AsyncIterator

# ============================================================================
# Set multiprocessing start method to 'spawn' BEFORE any imports
# This MUST happen before any CUDA/torch imports to avoid fork() issues
# with CUDA contexts in child processes.
# ============================================================================
with contextlib.suppress(RuntimeError):
    multiprocessing.set_start_method("spawn", force=True)

# ============================================================================
# Apply log noise filters BEFORE importing engine libraries
# This suppresses verbose TRT-LLM/vLLM output unless SHOW_*_LOGS is set.
# Must happen before any tensorrt_llm/vllm imports to set env vars early.
# ============================================================================
from src.scripts.filters import configure as configure_log_filters  # noqa: E402

configure_log_filters()

from fastapi import FastAPI  # noqa: E402
from fastapi import Request  # noqa: E402
from fastapi import WebSocket  # noqa: E402
from .logging import configure_logging  # noqa: E402
from .helpers.health import HealthNetwork  # noqa: E402
from fastapi.responses import ORJSONResponse  # noqa: E402
from .config.http import HEALTH_ALLOWED_CIDRS  # noqa: E402
from .helpers.health import parse_health_allowed_cidrs  # noqa: E402
from .helpers.health import ensure_internal_health_request  # noqa: E402

logger = logging.getLogger(__name__)

configure_logging()


def _get_health_allowed_cidrs(app: FastAPI) -> tuple[HealthNetwork, ...]:
    allowed_cidrs = getattr(app.state, "health_allowed_cidrs", None)
    if allowed_cidrs is None:
        allowed_cidrs = parse_health_allowed_cidrs(HEALTH_ALLOWED_CIDRS)
        app.state.health_allowed_cidrs = allowed_cidrs
    return allowed_cidrs


def _build_lifespan(*, validate_environment: bool):
    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        """Build and tear down runtime dependencies around app lifetime."""
        from .runtime import build_runtime_deps
        from .telemetry.sentry import capture_error
        from .helpers.validation import validate_env
        from .telemetry.setup import init_telemetry, shutdown_telemetry
        from .telemetry.instruments import get_metrics, initialize_metrics

        t0 = time.monotonic()
        if validate_environment:
            validate_env()
        app.state.health_allowed_cidrs = parse_health_allowed_cidrs(HEALTH_ALLOWED_CIDRS)
        init_telemetry()
        initialize_metrics()

        try:
            runtime_deps = await build_runtime_deps()
        except Exception as exc:
            capture_error(exc, extra={"phase": "bootstrap"})
            raise
        app.state.runtime_deps = runtime_deps

        if runtime_deps.supports_cache_reset():
            runtime_deps.ensure_cache_reset_daemon()
        else:
            logger.info("cache reset daemon: disabled (TRT-LLM uses block reuse)")

        get_metrics().startup_duration.record(time.monotonic() - t0)
        try:
            yield
        finally:
            shutdown_runtime_deps = getattr(app.state, "runtime_deps", None)
            try:
                if shutdown_runtime_deps is not None:
                    await shutdown_runtime_deps.shutdown()
            finally:
                shutdown_telemetry()

    return lifespan


def create_app(*, attach_lifecycle: bool = True, validate_environment: bool = True) -> FastAPI:
    """Create the FastAPI application."""
    app = FastAPI(
        default_response_class=ORJSONResponse,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_build_lifespan(validate_environment=validate_environment) if attach_lifecycle else None,
    )

    @app.get("/healthz")
    async def healthz(request: Request):
        """Internal-only health check endpoint."""
        ensure_internal_health_request(request, allowed_cidrs=_get_health_allowed_cidrs(request.app))
        return {"status": "ok"}

    @app.get("/favicon.ico", status_code=204)
    async def favicon():
        """Suppress favicon requests from browsers/probes."""
        return None

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        """Main WebSocket endpoint for chat interactions."""
        from .handlers.websocket.manager import handle_websocket_connection

        runtime_deps = getattr(app.state, "runtime_deps", None)
        if runtime_deps is None:
            raise RuntimeError("Runtime dependencies are not initialized")
        await handle_websocket_connection(websocket, runtime_deps)

    return app


app = create_app()
