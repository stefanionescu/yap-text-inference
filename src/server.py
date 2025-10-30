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
from .config.logging import APP_LOG_LEVEL, APP_LOG_FORMAT
from .handlers.websocket_handler import handle_websocket_connection
from .handlers.connection_handler import connection_handler
from .auth import get_api_key
from .tokens.tokenizer import get_tokenizer


app = FastAPI(default_response_class=ORJSONResponse)

# ---- Logging configuration ----
import logging

root_logger = logging.getLogger()
if not root_logger.handlers:
    logging.basicConfig(level=APP_LOG_LEVEL, format=APP_LOG_FORMAT)
else:
    root_logger.setLevel(APP_LOG_LEVEL)
    for _h in root_logger.handlers:
        try:
            _h.setLevel(APP_LOG_LEVEL)
        except Exception:
            pass

# Ensure our package logs are at least at APP_LOG_LEVEL
logging.getLogger("src").setLevel(APP_LOG_LEVEL)


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
    """Warm deployed engines so models are loaded BEFORE serving requests.

    This runs unconditionally at startup and blocks until the first token
    is produced for each deployed engine. This ensures engines, tokenizers,
    and weights are fully initialized before the server accepts traffic.
    """
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["\n", "</s>"])

    # Warm tokenizer used by exact trimming to avoid first-request stalls
    try:
        _ = get_tokenizer()
    except Exception as e:
        # Tokenizer warmup failures shouldn't block server start; generation warmups below will still proceed
        print(f"Warning: Tokenizer warmup failed: {e}")
        pass

    async def _warm(name: str, get_engine_fn, prompt: str, priority: int) -> None:
        try:
            rid = f"warm-{name}-{uuid.uuid4()}"
            engine = await get_engine_fn()
            stream = engine.generate(
                prompt=prompt,
                sampling_params=params,
                request_id=rid,
                priority=priority,
            )
            async for _ in stream:
                break
        except Exception as e:
            # Do not fail startup if warmup errors; models will still lazy-load
            print(f"Warning: warmup for {name} failed: {e}")

    tasks = []
    if DEPLOY_CHAT:
        tasks.append(_warm("chat", get_chat_engine, "<|persona|>\nWARM\n<|assistant|>\n", 0))
    if DEPLOY_TOOL:
        tasks.append(_warm("tool", get_tool_engine, "warmup", 1))
    if tasks:
        # Run warmups concurrently
        import asyncio as _asyncio
        await _asyncio.gather(*tasks)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint for chat interactions."""
    await handle_websocket_connection(websocket)