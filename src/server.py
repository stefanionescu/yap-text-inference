"""Main FastAPI server for vLLM-based inference stack."""

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
# Use 'spawn' for multiprocessing to avoid CUDA issues in forked subprocesses
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")
# Delay CUDA module loading to avoid early initialization issues
os.environ.setdefault("CUDA_MODULE_LOADING", "LAZY")
# Ensure CUDA_VISIBLE_DEVICES is set to avoid "changing after program start" errors
os.environ.setdefault("CUDA_VISIBLE_DEVICES", os.environ.get("CUDA_VISIBLE_DEVICES", "0"))

from fastapi import FastAPI, WebSocket
from fastapi.responses import ORJSONResponse

from .config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    CACHE_RESET_INTERVAL_SECONDS,
)
from .config.env import validate_env
from .config.logging import configure_logging
from .vllm import (
    cache_reset_reschedule_event,
    get_engine,
    reset_engine_caches,
    seconds_since_last_cache_reset,
    shutdown_engines,
)
from .handlers.websocket import handle_websocket_connection
from .handlers.connection_handler import connection_handler

logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()
validate_env()


_cache_reset_task: asyncio.Task | None = None


async def _warm_chat_engine(getter):
    """Ensure the chat engine is constructed before serving traffic."""
    start = time.perf_counter()
    logger.info("preload_engines: warming chat engine...")
    await getter()
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: chat engine ready in %.2fs", elapsed)


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
    """Load any configured vLLM engines before accepting traffic."""
    tasks: list[asyncio.Task[None]] = []

    if DEPLOY_CHAT:
        tasks.append(asyncio.create_task(_warm_chat_engine(get_engine)))

    if DEPLOY_TOOL:
        tasks.append(asyncio.create_task(_warm_classifier()))

    if not tasks:
        return

    logger.info("preload_engines: initializing %s engine(s)...", len(tasks))
    await asyncio.gather(*tasks)
    logger.info("preload_engines: all requested engines ready")

    _ensure_cache_reset_daemon()


@app.on_event("shutdown")
async def stop_engines() -> None:
    """Ensure all engines shut down cleanly when the server exits."""

    await shutdown_engines()


@app.get("/healthz")
async def healthz():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)


def _ensure_cache_reset_daemon() -> None:
    """Start the cache reset daemon if configuration enables it."""

    global _cache_reset_task
    if _cache_reset_task and not _cache_reset_task.done():
        return
    if CACHE_RESET_INTERVAL_SECONDS <= 0:
        return
    _cache_reset_task = asyncio.create_task(cache_reset_daemon())


async def cache_reset_daemon() -> None:
    """Background task to periodically reset vLLM caches."""

    interval = CACHE_RESET_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("cache reset daemon disabled")
        return

    event = cache_reset_reschedule_event()
    logger.info("cache reset daemon started interval=%ss", interval)

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
