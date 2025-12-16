"""Main FastAPI server for inference stack (vLLM or TensorRT-LLM)."""

from __future__ import annotations

import asyncio
import logging
import multiprocessing
import os
import time

# Set multiprocessing start method to 'spawn' before anything else
# This MUST happen before any CUDA/torch imports
try:
    multiprocessing.set_start_method("spawn", force=True)
except RuntimeError:
    pass  # Already set

# Set all CUDA/vLLM environment variables BEFORE any vLLM/torch imports
os.environ.setdefault("VLLM_USE_V1", "1")
os.environ.setdefault("ENFORCE_EAGER", "0")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))

from fastapi import FastAPI, WebSocket
from fastapi.responses import ORJSONResponse

from .config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CACHE_RESET_INTERVAL_SECONDS,
    INFERENCE_ENGINE,
)
from .config import validate_env
from .config.logging import configure_logging
from .engines import (
    get_engine,
    shutdown_engines,
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


_cache_reset_task: asyncio.Task | None = None


async def _warm_chat_engine(getter):
    """Ensure the chat engine is constructed before serving traffic."""
    start = time.perf_counter()
    engine_name = "TRT-LLM" if INFERENCE_ENGINE == "trt" else "vLLM"
    logger.info("preload_engines: warming %s chat engine...", engine_name)
    await getter()
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: %s chat engine ready in %.2fs", engine_name, elapsed)


async def _warm_classifier() -> None:
    """Ensure the classifier adapter is constructed before serving traffic."""
    from .classifier import get_classifier_adapter

    start = time.perf_counter()
    logger.info("preload_engines: warming tool classifier adapter...")
    await asyncio.to_thread(get_classifier_adapter)
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: tool classifier ready in %.2fs", elapsed)


@app.on_event("startup")
async def preload_engines() -> None:
    """Load any configured engines before accepting traffic."""
    tasks: list[asyncio.Task[None]] = []

    if DEPLOY_CHAT:
        tasks.append(asyncio.create_task(_warm_chat_engine(get_engine)))

    if DEPLOY_TOOL:
        tasks.append(asyncio.create_task(_warm_classifier()))

    if not tasks:
        return

    await asyncio.gather(*tasks)

    # Only start cache reset daemon for engines that support it (vLLM)
    if engine_supports_cache_reset():
        _ensure_cache_reset_daemon()
    else:
        logger.info("cache reset daemon: disabled (TRT-LLM uses block reuse)")


@app.on_event("shutdown")
async def stop_engines() -> None:
    """Ensure all engines shut down cleanly when the server exits."""
    await shutdown_engines()


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
    
    Note: Only called for vLLM. TRT-LLM uses block reuse and doesn't need this.
    """
    global _cache_reset_task
    if _cache_reset_task and not _cache_reset_task.done():
        return
    if CACHE_RESET_INTERVAL_SECONDS <= 0:
        return
    _cache_reset_task = asyncio.create_task(cache_reset_daemon())


async def cache_reset_daemon() -> None:
    """Background task to periodically reset vLLM caches.
    
    This daemon only runs for vLLM. TRT-LLM handles memory management
    through its built-in KV cache block reuse mechanism.
    """
    interval = CACHE_RESET_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("cache reset daemon disabled")
        return

    event = cache_reset_reschedule_event()
    logger.info("cache reset daemon started interval=%ss (vLLM only)", interval)

    while True:
        if event.is_set():
            event.clear()
            continue

        wait = max(0.0, interval - seconds_since_last_cache_reset())
        if wait <= 0:
            await reset_engine_caches("timer", force=True)
            continue

        try:
            await asyncio.wait_for(event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            await reset_engine_caches("timer", force=True)
        else:
            if event.is_set():
                event.clear()
