"""FastAPI server entrypoint."""

import asyncio
import logging

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

# Load environment variables early to ensure config reads correct values
load_dotenv(".env")

from server.auth.utils import ensure_hf_login  # noqa: E402
from server.config import settings  # noqa: E402
from server.engine import OrpheusTRTEngine as _Engine  # noqa: E402
from server.streaming.pipeline.streaming_pipeline import StreamingPipeline  # noqa: E402
from server.streaming.ws.connection_state import ConnectionState  # noqa: E402
from server.streaming.ws.handshake import HandshakeGateway  # noqa: E402
from server.streaming.ws.lifecycle import SessionLifecycle  # noqa: E402
from server.streaming.ws.message_receiver import message_receiver  # noqa: E402
from server.streaming.ws.synthesis_handler import synthesis_handler  # noqa: E402
from server.streaming.ws.utils import safe_ws_close  # noqa: E402

logger = logging.getLogger(__name__)

HOST = settings.host
PORT = settings.port
SAMPLE_RATE = settings.snac_sr

app = FastAPI(title=settings.api_title)

app.state.engine = None
app.state.conn_semaphore = None
app.state.active_connections = 0
HANDSHAKE = HandshakeGateway()


@app.on_event("startup")
async def _startup():
    # Enforce required secrets before initializing engine
    if not settings.api_key:
        raise RuntimeError("ORPHEUS_API_KEY is required but not set. Set env var ORPHEUS_API_KEY.")
    ensure_hf_login()
    app.state.engine = _Engine()
    # Initialize global concurrency semaphore
    app.state.conn_semaphore = asyncio.Semaphore(settings.ws_max_connections)


@app.get(settings.http_health_path)
async def healthz():
    return {"ok": True}


@app.get("/health")
async def health_alias():
    return {"ok": True}


@app.websocket(settings.ws_tts_path)
async def tts_ws(ws: WebSocket):
    """
    Sentence-by-sentence WS:
      - Client sends {"text": "...sentence or full text...", "voice": "..."}.
      - Server splits text into sentences only (no word-based chunking).
      - For each sentence, runs one generation and streams audio hops.
      - Strict in-order emission; no timers, no word buffering.
    """
    # Authorization before accepting the WebSocket
    if not await HANDSHAKE.authorize(ws):
        return
    # Enforce capacity via semaphore (race-free)
    sem, acquired = await HANDSHAKE.acquire_capacity(app, ws)
    if not acquired:
        return
    # Validate engine availability before accepting
    engine = await HANDSHAKE.ensure_engine(app, ws, sem, acquired)
    if engine is None:
        return
    # Only accept once authorized and capacity acquired
    await ws.accept()

    # Initialize clean handlers
    message_queue: asyncio.Queue[dict | None] = asyncio.Queue(maxsize=settings.ws_queue_maxsize)
    cancel_event: asyncio.Event = asyncio.Event()
    connection_state = ConnectionState()
    streaming_pipeline = StreamingPipeline(engine)

    # Session lifecycle tracking (no inline magic values)
    lifecycle = SessionLifecycle(ws)

    try:
        recv_task = asyncio.create_task(message_receiver(ws, message_queue, cancel_event, lifecycle.touch))
        synth_task = asyncio.create_task(
            synthesis_handler(ws, message_queue, cancel_event, connection_state, streaming_pipeline, lifecycle.touch)
        )
        # Run watchdog independently; do not block session teardown on it
        watchdog_task = asyncio.create_task(lifecycle.watchdog())
        # Wait for receiver and synthesis to complete; collect exceptions without bubbling
        await asyncio.gather(recv_task, synth_task, return_exceptions=True)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.exception("WebSocket error: %s", e)
    finally:
        # Ensure background tasks are stopped promptly
        for t in (recv_task, synth_task, watchdog_task):
            import contextlib

            with contextlib.suppress(Exception):
                t.cancel()
        await safe_ws_close(ws)
        # Release capacity slot if acquired
        if acquired and sem is not None:
            with contextlib.suppress(Exception):
                sem.release()
