"""Main FastAPI server for the Yap Text Inference stack.

This module initializes and runs the inference server, supporting both vLLM and
TensorRT-LLM backends. It provides:

- REST endpoints for health checks (/healthz, /)
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
import time

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

from fastapi import FastAPI, WebSocket
from fastapi.responses import ORJSONResponse

from .config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CACHE_RESET_INTERVAL_SECONDS,
    INFERENCE_ENGINE,
)
from .helpers.validation import validate_env
from .config.logging import configure_logging
from .engines import (
    get_engine,
    shutdown_engine,
    reset_engine_caches,
    cache_reset_reschedule_event,
    seconds_since_last_cache_reset,
    engine_supports_cache_reset,
)
from .handlers.websocket import handle_websocket_connection

logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()
validate_env()


# Global task reference for the cache reset daemon
# This allows the daemon to be stopped on shutdown
_cache_reset_task: asyncio.Task | None = None


async def _warm_chat_engine(getter):
    """Ensure the chat engine is constructed before serving traffic.
    
    This pre-warms the inference engine during server startup, which:
    - Loads model weights into GPU memory
    - Compiles CUDA kernels (if using vLLM)
    - Validates the configuration
    
    Args:
        getter: Async callable that returns the engine instance.
    
    Note:
        For vLLM, this can take 30-60 seconds for large models.
        For TRT-LLM, this loads pre-compiled engines and is faster.
    """
    start = time.perf_counter()
    engine_name = "TRT-LLM" if INFERENCE_ENGINE == "trt" else "vLLM"
    logger.info("preload_engines: warming %s chat engine...", engine_name)
    await getter()
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: %s chat engine ready in %.2fs", engine_name, elapsed)


async def _warm_classifier() -> None:
    """Ensure the classifier adapter is constructed before serving traffic.
    
    The classifier is a lightweight PyTorch model used for screenshot
    intent detection. It runs separately from the main chat engine and
    is much faster to load (~5-10 seconds).
    
    This runs in a thread pool to avoid blocking the event loop during
    model loading.
    """
    from .classifier import get_classifier_adapter

    start = time.perf_counter()
    logger.info("preload_engines: warming tool classifier adapter...")
    # Run in thread pool - model loading is synchronous and blocking
    await asyncio.to_thread(get_classifier_adapter)
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: tool classifier ready in %.2fs", elapsed)


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
        tasks.append(asyncio.create_task(_warm_chat_engine(get_engine)))

    if DEPLOY_TOOL:
        tasks.append(asyncio.create_task(_warm_classifier()))

    if not tasks:
        return

    # Wait for all engines to be ready
    await asyncio.gather(*tasks)

    # Start background cache management for vLLM
    # TRT-LLM uses built-in block reuse and doesn't need this
    if engine_supports_cache_reset():
        _ensure_cache_reset_daemon()
    else:
        logger.info("cache reset daemon: disabled (TRT-LLM uses block reuse)")


@app.on_event("shutdown")
async def stop_engines() -> None:
    """Ensure all engines shut down cleanly when the server exits."""
    await shutdown_engine()


@app.get("/")
async def root():
    """Root endpoint for load balancer health checks."""
    return {"status": "ok", "engine": INFERENCE_ENGINE}


@app.get("/healthz")
async def healthz():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok", "engine": INFERENCE_ENGINE}


@app.get("/favicon.ico", status_code=204)
async def favicon():
    """Suppress favicon requests from browsers/probes."""
    return None


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)


def _ensure_cache_reset_daemon() -> None:
    """Start the cache reset daemon if configuration enables it.
    
    The cache reset daemon periodically clears vLLM's prefix cache and
    multimodal cache to prevent memory fragmentation over time. This is
    especially important for:
    - Long-running deployments
    - High-volume traffic with diverse prompts
    - Models with prefix caching enabled
    
    Note:
        Only called for vLLM. TRT-LLM uses block reuse and handles memory
        management differently (no periodic reset needed).
    """
    global _cache_reset_task
    # Don't start if already running
    if _cache_reset_task and not _cache_reset_task.done():
        return
    # Don't start if cache reset is disabled
    if CACHE_RESET_INTERVAL_SECONDS <= 0:
        return
    _cache_reset_task = asyncio.create_task(cache_reset_daemon())


async def cache_reset_daemon() -> None:
    """Background task to periodically reset vLLM caches.
    
    This daemon runs on a configurable interval (default 600s) and:
    1. Resets the prefix cache (frees computed attention states)
    2. Resets the multimodal cache (frees image/audio embeddings)
    
    The daemon uses an event-based scheduling system that can be interrupted
    when a long session ends, triggering an immediate reset instead of
    waiting for the timer.
    
    Note:
        This daemon only runs for vLLM. TRT-LLM handles memory management
        through its built-in KV cache block reuse mechanism, which
        automatically reclaims memory without explicit resets.
    """
    interval = CACHE_RESET_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("cache reset daemon disabled")
        return

    # Event used to interrupt the wait (e.g., after a long session ends)
    event = cache_reset_reschedule_event()
    logger.info("cache reset daemon started interval=%ss", interval)

    while True:
        # Check if we were signaled to reset immediately
        if event.is_set():
            event.clear()
            continue

        # Calculate remaining wait time
        wait = max(0.0, interval - seconds_since_last_cache_reset())
        if wait <= 0:
            # Timer expired - reset caches now
            await reset_engine_caches("timer", force=True)
            continue

        try:
            # Wait for either the timer or an interrupt signal
            await asyncio.wait_for(event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            # Timer expired - reset caches
            await reset_engine_caches("timer", force=True)
        else:
            # Event was set - someone requested a reschedule
            if event.is_set():
                event.clear()
