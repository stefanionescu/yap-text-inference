"""Main FastAPI server for vLLM-based inference stack."""

from __future__ import annotations

import os

# Ensure V1 engine flag is set before importing any vLLM modules in this process
os.environ.setdefault("VLLM_USE_V1", "1")
os.environ.setdefault("ENFORCE_EAGER", "0")

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import ORJSONResponse

from .config.env import validate_env
from .config.logging import configure_logging
from .handlers.websocket_handler import handle_websocket_connection
from .handlers.connection_handler import connection_handler
from .auth import get_api_key
from .startup import StartupWarmup


app = FastAPI(default_response_class=ORJSONResponse)

configure_logging()
validate_env()
_warmup_service = StartupWarmup()


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


@app.on_event("startup")
async def startup_warmup():
    """Warm deployed engines so models are loaded before serving requests."""
    await _warmup_service.run()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)