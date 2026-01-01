"""Connection lifecycle regression helpers.

Provides async helpers for exercising the `/ws` endpoint with several
connection scenarios (normal close, rapid churn, ping/pong, and idle
watchdog). The CLI wrapper in `tests/connections.py` parses arguments
and invokes `run_connection_suite`.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import websockets

from tests.config import DEFAULT_WS_PING_INTERVAL, DEFAULT_WS_PING_TIMEOUT
from tests.helpers.ws import connect_with_retries, send_client_end

logger = logging.getLogger("connections")


def _open_connection(ws_url: str):
    return connect_with_retries(
        lambda: websockets.connect(
            ws_url,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        )
    )


async def _test_normal_connection(ws_url: str, wait_seconds: float) -> None:
    async with _open_connection(ws_url) as ws:
        logger.info("[normal] connected; sleeping for %.1fs", wait_seconds)
        await asyncio.sleep(max(0.0, wait_seconds))
        await send_client_end(ws)
        logger.info("[normal] graceful close sent")


async def _test_quick_connect_close(ws_url: str) -> None:
    async with _open_connection(ws_url) as ws:
        logger.info("[quick] connected; sending end immediately")
        await send_client_end(ws)
        logger.info("[quick] close frame flushed")


async def _test_ping_pong(ws_url: str) -> None:
    async with _open_connection(ws_url) as ws:
        logger.info("[ping] sending ping control frame")
        await ws.send(json.dumps({"type": "ping"}))
        try:
            payload = await asyncio.wait_for(ws.recv(), timeout=5.0)
        except asyncio.TimeoutError:
            raise RuntimeError("no pong response within 5s")
        msg = json.loads(payload)
        if msg.get("type") != "pong":
            raise RuntimeError(f"expected pong, got {msg.get('type')}")
        logger.info("[ping] received pong response")
        await send_client_end(ws)


async def _test_idle_watchdog(
    ws_url: str,
    expect_seconds: float,
    grace_seconds: float,
) -> None:
    total_wait = max(0.0, expect_seconds) + max(0.0, grace_seconds)
    if total_wait == 0:
        raise RuntimeError("idle wait is zero; use --idle-expect-seconds")

    async with _open_connection(ws_url) as ws:
        logger.info(
            "[idle] waiting up to %.1fs for server to close idle connection",
            total_wait,
        )
        try:
            await asyncio.wait_for(ws.recv(), timeout=total_wait)
            raise RuntimeError("server sent data before idle close")
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"server did not close within {total_wait:.0f}s "
                f"(expected idle timeout: {expect_seconds:.0f}s)"
            )
        except websockets.ConnectionClosed as exc:
            logger.info(
                "[idle] server closed connection (code=%s reason=%s)",
                exc.code,
                exc.reason,
            )


async def run_connection_suite(
    ws_url: str,
    *,
    normal_wait_s: float,
    idle_expect_s: float,
    idle_grace_s: float,
) -> bool:
    """Run the connection lifecycle scenarios sequentially."""

    tests: list[tuple[str, Callable[[], Awaitable[None]]]] = [
        ("normal", lambda: _test_normal_connection(ws_url, normal_wait_s)),
        ("quick", lambda: _test_quick_connect_close(ws_url)),
        ("ping", lambda: _test_ping_pong(ws_url)),
        (
            "idle",
            lambda: _test_idle_watchdog(
                ws_url,
                idle_expect_s,
                idle_grace_s,
            ),
        ),
    ]

    success = True
    for label, factory in tests:
        logger.info("==== Running %s connection test ====", label)
        try:
            await factory()
            logger.info("[%s] PASS", label)
        except Exception as exc:  # noqa: BLE001
            success = False
            logger.error("[%s] FAIL: %s", label, exc)
    return success


__all__ = ["run_connection_suite"]
