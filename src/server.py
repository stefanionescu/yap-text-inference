"""Main FastAPI server for vLLM-based inference stack."""

from __future__ import annotations

import os
import uuid

# Ensure V1 engine flag is set before importing any vLLM modules in this process
os.environ.setdefault("VLLM_USE_V1", "1")
os.environ.setdefault("ENFORCE_EAGER", "0")

from fastapi import FastAPI, WebSocket, Depends
from fastapi.responses import ORJSONResponse
from vllm.sampling_params import SamplingParams

from .engines import get_chat_engine, get_tool_engine
from .config import DEPLOY_CHAT, DEPLOY_TOOL
from .handlers.websocket_handler import handle_websocket_connection
from .handlers.connection_manager import connection_manager
from .auth import get_api_key


app = FastAPI(default_response_class=ORJSONResponse)


@app.get("/healthz")
async def healthz():
    """Health check endpoint (no authentication required)."""
    return {"status": "ok"}


@app.get("/status")
async def status(api_key: str = Depends(get_api_key)):
    """Server status and capacity information (requires authentication)."""
    capacity = connection_manager.get_capacity_info()
    return {
        "status": "running",
        "connections": capacity,
        "healthy": not capacity["at_capacity"]
    }


@app.on_event("startup")
async def startup_warmup():
    """Warm deployed engines to reduce first-turn TTFT."""
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["\n", "</s>"])

    if DEPLOY_CHAT:
        rid_c = f"warm-chat-{uuid.uuid4()}"
        stream_c = (await get_chat_engine()).generate(
            prompt="<|persona|>\nWARM\n<|assistant|>\n",
            sampling_params=params,
            request_id=rid_c,
            priority=1,
        )
        async for _ in stream_c:
            break

    if DEPLOY_TOOL:
        rid_t = f"warm-tool-{uuid.uuid4()}"
        stream_t = (await get_tool_engine()).generate(
            prompt="warmup",
            sampling_params=params,
            request_id=rid_t,
            priority=1,
        )
        async for _ in stream_t:
            break


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)