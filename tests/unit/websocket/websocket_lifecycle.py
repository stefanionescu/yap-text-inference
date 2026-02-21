"""Unit tests for websocket lifecycle idle-timeout signaling."""

from __future__ import annotations

import asyncio
from src.config.websocket import WS_CLOSE_IDLE_REASON
from src.handlers.websocket.lifecycle import WebSocketLifecycle


class _FakeWebSocket:
    def __init__(self) -> None:
        self.close_calls: list[tuple[int, str]] = []

    async def close(self, *, code: int, reason: str) -> None:
        self.close_calls.append((code, reason))


def test_lifecycle_sets_idle_timeout_flag_and_closes_socket() -> None:
    async def _run() -> None:
        ws = _FakeWebSocket()
        lifecycle = WebSocketLifecycle(
            ws,
            idle_timeout_s=0.02,
            watchdog_tick_s=0.005,
            idle_close_code=4444,
        )
        lifecycle.start()
        await asyncio.sleep(0.06)
        await lifecycle.stop()

        assert lifecycle.idle_timed_out()
        assert ws.close_calls == [(4444, WS_CLOSE_IDLE_REASON)]

    asyncio.run(_run())


def test_lifecycle_stop_before_timeout_does_not_mark_idle_timeout() -> None:
    async def _run() -> None:
        ws = _FakeWebSocket()
        lifecycle = WebSocketLifecycle(
            ws,
            idle_timeout_s=1.0,
            watchdog_tick_s=0.05,
        )
        lifecycle.start()
        await asyncio.sleep(0.01)
        await lifecycle.stop()

        assert not lifecycle.idle_timed_out()
        assert ws.close_calls == []

    asyncio.run(_run())
