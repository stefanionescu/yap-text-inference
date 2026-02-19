"""Main FastAPI server for the Yap Text Inference stack.

This module initializes and runs the inference server, supporting both vLLM and
TensorRT-LLM backends. It provides:

- REST endpoints for health checks (/health, /healthz, /)
- WebSocket endpoint for chat interactions (/ws)
- Automatic engine warm-up on startup
- Periodic cache reset for vLLM (prevents KV cache fragmentation)
- Graceful shutdown with engine cleanup

Server Lifecycle:
    1. On startup: Preload configured engines (chat and/or tool)
    2. Accept WebSocket connections on /ws
    3. Route messages through handlers (start, followup, cancel, etc.)
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

from fastapi import FastAPI, WebSocket  # noqa: E402
from fastapi.responses import ORJSONResponse  # noqa: E402

from .logging import configure_logging  # noqa: E402
from .runtime import build_runtime_deps  # noqa: E402
from .telemetry.sentry import capture_error  # noqa: E402
from .helpers.validation import validate_env  # noqa: E402
from .runtime.bootstrap import clear_runtime_registries  # noqa: E402
from .handlers.websocket import handle_websocket_connection  # noqa: E402
from .telemetry.setup import init_telemetry, shutdown_telemetry  # noqa: E402
from .telemetry.instruments import get_metrics, initialize_metrics  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()

validate_env()


@app.on_event("startup")
async def preload_engines() -> None:
    """Build all runtime dependencies before accepting traffic."""
    t0 = time.monotonic()
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


@app.on_event("shutdown")
async def stop_engines() -> None:
    """Ensure runtime dependencies shut down cleanly."""
    runtime_deps = getattr(app.state, "runtime_deps", None)
    try:
        if runtime_deps is not None:
            await runtime_deps.shutdown()
    finally:
        clear_runtime_registries()
        shutdown_telemetry()


@app.get("/")
async def root():
    """Root endpoint for load balancer health checks."""
    return {"status": "ok"}


@app.get("/health")
async def health():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok"}


@app.get("/favicon.ico", status_code=204)
async def favicon():
    """Suppress favicon requests from browsers/probes."""
    return None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    runtime_deps = getattr(app.state, "runtime_deps", None)
    if runtime_deps is None:
        raise RuntimeError("Runtime dependencies are not initialized")
    await handle_websocket_connection(websocket, runtime_deps)
