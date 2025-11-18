"""Per-connection WebSocket lifecycle helpers (idle enforcement)."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from fastapi import WebSocket

from ..config.websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_WATCHDOG_TICK_S,
    WS_CLOSE_IDLE_CODE,
)

logger = logging.getLogger(__name__)


class WebSocketLifecycle:
    """Tracks activity timestamps and enforces idle timeouts."""

    def __init__(
        self,
        websocket: WebSocket,
        idle_timeout_s: float | None = None,
        watchdog_tick_s: float | None = None,
        idle_close_code: int | None = None,
    ):
        self._ws = websocket
        self._idle_timeout_s = float(idle_timeout_s or WS_IDLE_TIMEOUT_S)
        self._watchdog_tick_s = float(watchdog_tick_s or WS_WATCHDOG_TICK_S)
        self._idle_close_code = idle_close_code if idle_close_code is not None else WS_CLOSE_IDLE_CODE
        self._last_activity = time.monotonic()
        self._stop_event = asyncio.Event()
        self._task: asyncio.Task | None = None

    def touch(self) -> None:
        """Record recent activity (resets idle countdown)."""
        self._last_activity = time.monotonic()

    def start(self) -> asyncio.Task:
        """Start the watchdog task (idempotent)."""
        if self._task is None:
            self._task = asyncio.create_task(self._watchdog_loop())
        return self._task

    async def stop(self) -> None:
        """Stop the watchdog task and wait for it to finish."""
        self._stop_event.set()
        if self._task is None:
            return
        self._task.cancel()
        with contextlib.suppress(Exception):
            await self._task
        self._task = None

    async def _watchdog_loop(self) -> None:
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._watchdog_tick_s)
                if self._stop_event.is_set():
                    break
                if (time.monotonic() - self._last_activity) >= self._idle_timeout_s:
                    logger.info("WebSocket idle timeout reached; closing connection")
                    await self._close_ws()
                    break
        except asyncio.CancelledError:
            pass
        except Exception:
            logger.debug("Idle watchdog exiting due to unexpected error", exc_info=True)

    async def _close_ws(self) -> None:
        with contextlib.suppress(Exception):
            await self._ws.close(code=self._idle_close_code)


__all__ = ["WebSocketLifecycle"]

