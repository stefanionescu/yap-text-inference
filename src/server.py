"""Main FastAPI server for the Yap Text Inference stack.

This module initializes and runs the inference server, supporting both vLLM and
TensorRT-LLM backends. It provides:

- REST endpoints for health checks (/health, /healthz, /)
- WebSocket endpoint for chat interactions (/ws)
- Automatic engine warm-up on startup
- Periodic cache reset for vLLM (prevents KV cache fragmentation)
- Graceful shutdown with engine cleanup

Server Lifecycle:
    1. On startup: Preload configured engines (chat and/or classifier)
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

import asyncio
import logging
import multiprocessing
import os

# ============================================================================
# CRITICAL: Set multiprocessing start method to 'spawn' BEFORE any imports
# This MUST happen before any CUDA/torch imports to avoid fork() issues
# with CUDA contexts in child processes.
# ============================================================================
try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass  # Already set - happens when running under certain test frameworks

# ============================================================================
# Set CUDA/vLLM environment variables BEFORE any vLLM/torch imports
# These control engine behavior and must be set early in the process.
# ============================================================================
os.environ.setdefault("VLLM_USE_V1", "1")  # Use vLLM V1 engine (better performance)
os.environ.setdefault("ENFORCE_EAGER", "0")  # Allow CUDA graphs
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")  # Match main process
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")  # Faster startup
os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))

# ============================================================================
# Apply log noise filters BEFORE importing engine libraries
# This suppresses verbose TRT-LLM/vLLM output unless SHOW_*_LOGS is set.
# Must happen before any tensorrt_llm/vllm imports to set env vars early.
# ============================================================================
from src.scripts.filters import configure as configure_log_filters
configure_log_filters()

from fastapi import FastAPI, WebSocket
from fastapi.responses import ORJSONResponse

from .config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    INFERENCE_ENGINE,
)
from .helpers.validation import validate_env
from .config.logging import configure_logging
from .engines import (
    get_engine,
    shutdown_engine,
    engine_supports_cache_reset,
    warm_chat_engine,
    warm_classifier,
)
from .handlers.websocket import handle_websocket_connection

logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()

# Engine-specific runtime setup - only load vLLM modules when using vLLM
if INFERENCE_ENGINE == "vllm":
    from .engines.vllm.setup import configure_runtime_env
    configure_runtime_env()

validate_env()


@app.on_event("startup")
async def preload_engines() -> None:
    """Load any configured engines before accepting traffic.
    
    This startup hook ensures models are loaded and ready before the
    server starts accepting WebSocket connections. Benefits:
    - First request doesn't incur model loading latency
    - Configuration errors are caught at startup
    - Load balancers can check /healthz after warmup completes
    
    The chat engine and classifier are warmed concurrently to minimize
    total startup time.
    """
    tasks: list[asyncio.Task[None]] = []

    # Warm engines concurrently based on deployment configuration
    if DEPLOY_CHAT:
        tasks.append(asyncio.create_task(warm_chat_engine(get_engine)))

    if DEPLOY_TOOL:
        tasks.append(asyncio.create_task(warm_classifier()))

    if not tasks:
        return

    # Wait for all engines to be ready
    await asyncio.gather(*tasks)

    # Start background cache management for vLLM
    # TRT-LLM uses built-in block reuse and doesn't need this
    if engine_supports_cache_reset():
        from .engines.vllm.cache_daemon import ensure_cache_reset_daemon
        ensure_cache_reset_daemon()
    else:
        logger.info("cache reset daemon: disabled (TRT-LLM uses block reuse)")


@app.on_event("shutdown")
async def stop_engines() -> None:
    """Ensure all engines shut down cleanly when the server exits."""
    await shutdown_engine()


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
    await handle_websocket_connection(websocket)
