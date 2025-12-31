"""Per-connection WebSocket lifecycle helpers (idle enforcement).

This module implements idle timeout enforcement for WebSocket connections.
Each connection gets a WebSocketLifecycle instance that:

1. Tracks last activity timestamp (updated via touch())
2. Runs a background watchdog task that checks for idleness
3. Closes the connection automatically when idle timeout is reached

This prevents resource exhaustion from abandoned connections (e.g., client
crashed, network dropped) that would otherwise stay open indefinitely.

The watchdog runs periodically (WS_WATCHDOG_TICK_S) and compares the
last activity time against the idle timeout (WS_IDLE_TIMEOUT_S).

Usage:
    lifecycle = WebSocketLifecycle(websocket)
    lifecycle.start()  # Start watchdog
    
    # In message loop:
    lifecycle.touch()  # Reset idle timer
    
    # On cleanup:
    await lifecycle.stop()
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time

from fastapi import WebSocket

from ...config.websocket import (
    WS_IDLE_TIMEOUT_S,
    WS_WATCHDOG_TICK_S,
    WS_CLOSE_IDLE_CODE,
    WS_CLOSE_IDLE_REASON,
)

logger = logging.getLogger(__name__)


class WebSocketLifecycle:
    """Tracks activity timestamps and enforces idle timeouts.
    
    This class manages the lifecycle of a single WebSocket connection,
    specifically handling idle timeout detection and enforcement.
    
    Attributes:
        _ws: The WebSocket connection being managed.
        _idle_timeout_s: Seconds of inactivity before closing.
        _watchdog_tick_s: How often to check for idleness.
        _last_activity: Monotonic timestamp of last activity.
    """

    def __init__(
        self,
        websocket: WebSocket,
        idle_timeout_s: float | None = None,
        watchdog_tick_s: float | None = None,
        idle_close_code: int | None = None,
    ):
        """Initialize lifecycle manager for a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to manage.
            idle_timeout_s: Override for idle timeout (defaults to config).
            watchdog_tick_s: Override for check interval (defaults to config).
            idle_close_code: WebSocket close code for idle disconnect.
        """
        self._ws = websocket
        self._idle_timeout_s = float(idle_timeout_s or WS_IDLE_TIMEOUT_S)
        self._watchdog_tick_s = float(watchdog_tick_s or WS_WATCHDOG_TICK_S)
        self._idle_close_code = (
            idle_close_code if idle_close_code is not None else WS_CLOSE_IDLE_CODE
        )
        self._idle_close_reason = WS_CLOSE_IDLE_REASON
        self._last_activity = time.monotonic()
        self._stop_event = asyncio.Event()  # Signals watchdog to stop
        self._task: asyncio.Task | None = None  # Watchdog task reference

    def touch(self) -> None:
        """Record recent activity (resets idle countdown)."""

        self._last_activity = time.monotonic()

    def should_close(self) -> bool:
        """Check if the connection should be closed (idle timeout fired)."""

        return self._stop_event.is_set()

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
        """Background loop that periodically checks for idle connections.
        
        Runs until stopped or idle timeout is reached. Closes the WebSocket
        with an appropriate code when idle timeout expires.
        """
        try:
            while not self._stop_event.is_set():
                await asyncio.sleep(self._watchdog_tick_s)
                if self._stop_event.is_set():
                    break
                # Check if connection has been idle too long
                if (time.monotonic() - self._last_activity) >= self._idle_timeout_s:
                    logger.info("WebSocket idle timeout reached; closing connection")
                    self._stop_event.set()  # Signal handler to exit
                    await self._close_ws()
                    break
        except asyncio.CancelledError:
            pass  # Normal shutdown path
        except Exception:
            logger.debug("Idle watchdog exiting due to unexpected error", exc_info=True)

    async def _close_ws(self) -> None:
        """Close the WebSocket with idle timeout code/reason."""
        with contextlib.suppress(Exception):
            await self._ws.close(code=self._idle_close_code, reason=self._idle_close_reason)


__all__ = ["WebSocketLifecycle"]


