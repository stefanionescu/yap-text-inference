"""WebSocket handshake helpers with consistent naming."""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import FastAPI, WebSocket

from server.config import settings
from server.streaming.ws.utils import authorize_ws, safe_ws_close

__all__ = ["HandshakeGateway"]


class HandshakeGateway:
    """Encapsulate the authorization → capacity → engine validation flow."""

    def __init__(self):
        self._logger = logging.getLogger(__name__)

    async def authorize(self, ws: WebSocket) -> bool:
        """Authorize the WebSocket or close with 1008."""
        if await authorize_ws(ws):
            return True
        self._logger.info("WS reject 403 unauthorized (missing/invalid Authorization header)")
        await safe_ws_close(ws, settings.ws_close_unauthorized_code)
        return False

    async def acquire_capacity(self, app: FastAPI, ws: WebSocket) -> tuple[asyncio.Semaphore | None, bool]:
        """Acquire a semaphore slot or close with busy code."""
        sem: asyncio.Semaphore | None = getattr(app.state, "conn_semaphore", None)
        if sem is None:
            self._logger.info("WS reject busy (semaphore not initialized)")
            await safe_ws_close(ws, settings.ws_close_busy_code)
            return None, False
        try:
            await asyncio.wait_for(sem.acquire(), timeout=float(settings.ws_handshake_acquire_timeout_s))
            return sem, True
        except asyncio.TimeoutError:
            self._logger.info("WS reject busy (max connections reached)")
            await safe_ws_close(ws, settings.ws_close_busy_code)
            return sem, False

    async def ensure_engine(self, app: FastAPI, ws: WebSocket, sem: asyncio.Semaphore | None, acquired: bool):
        """Ensure engine is available before accept. Close with busy if not."""
        engine = getattr(app.state, "engine", None)
        if engine is not None:
            return engine
        self._logger.info("WS reject busy (engine unavailable)")
        await safe_ws_close(ws, settings.ws_close_busy_code)
        if acquired and sem is not None:
            with contextlib.suppress(Exception):
                sem.release()
        return None
