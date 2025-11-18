"""Main FastAPI server for vLLM-based inference stack."""

from __future__ import annotations

import asyncio
import logging
import os
import time

# Ensure V1 engine flag is set before importing any vLLM modules in this process
os.environ.setdefault("VLLM_USE_V1", "1")
os.environ.setdefault("ENFORCE_EAGER", "0")

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import ORJSONResponse

from .config import DEPLOY_CHAT, DEPLOY_TOOL
from .config.env import validate_env
from .config.logging import configure_logging
from .engines import get_chat_engine, get_tool_engine
from .handlers.websocket_handler import handle_websocket_connection
from .handlers.connection_handler import connection_handler
from .auth import get_api_key


logger = logging.getLogger(__name__)

app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()
validate_env()


async def _warm_engine(name: str, getter):
    """Ensure the requested engine is constructed before serving traffic."""
    start = time.perf_counter()
    logger.info("preload_engines: warming %s engine...", name)
    await getter()
    elapsed = time.perf_counter() - start
    logger.info("preload_engines: %s engine ready in %.2fs", name, elapsed)


@app.on_event("startup")
async def preload_engines() -> None:
    """Load any configured vLLM engines before accepting traffic."""
    tasks: list[asyncio.Task[None]] = []

    if DEPLOY_CHAT:
        tasks.append(asyncio.create_task(_warm_engine("chat", get_chat_engine)))
    if DEPLOY_TOOL:
        tasks.append(asyncio.create_task(_warm_engine("tool", get_tool_engine)))

    if not tasks:
        return

    logger.info("preload_engines: initializing %s engine(s)...", len(tasks))
    await asyncio.gather(*tasks)
    logger.info("preload_engines: all requested engines ready")


@app.get("/healthz")
async def healthz():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok"}


@app.get("/status")
async def status(api_key: str = Depends(get_api_key)):
    """Server status and capacity information (requires authentication)."""
    capacity = connection_handler.get_capacity_info()
    return {
        "status": "running",
        "connections": capacity,
        "healthy": not capacity["at_capacity"]
    }


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)