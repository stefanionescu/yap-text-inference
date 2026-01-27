"""Idle timeout and connection lifecycle regression helpers.

Provides async helpers for exercising the `/ws` endpoint with several
connection scenarios (normal close, rapid churn, ping/pong, and idle
watchdog). The CLI wrapper in `tests/idle.py` parses arguments
and invokes `run_idle_suite`.
"""

from __future__ import annotations

import json
import asyncio
from collections.abc import Callable, Awaitable

import websockets

from tests.helpers.websocket import send_client_end, connect_with_retries
from tests.config import DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.helpers.fmt import (
    dim,
    section_header,
    connection_fail,
    connection_pass,
    connection_status,
    connection_test_header,
)


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
        print(connection_status("normal", f"connected, sleeping {wait_seconds:.1f}s..."))
        await asyncio.sleep(max(0.0, wait_seconds))
        await send_client_end(ws)
        print(connection_status("normal", "graceful close sent"))


async def _test_quick_connect_close(ws_url: str) -> None:
    async with _open_connection(ws_url) as ws:
        print(connection_status("quick", "connected, closing immediately..."))
        await send_client_end(ws)
        print(connection_status("quick", "close frame flushed"))


async def _test_ping_pong(ws_url: str) -> None:
    async with _open_connection(ws_url) as ws:
        print(connection_status("ping", "sending ping frame..."))
        await ws.send(json.dumps({"type": "ping"}))
        try:
            payload = await asyncio.wait_for(ws.recv(), timeout=5.0)
        except asyncio.TimeoutError:
            raise RuntimeError("no pong response within 5s") from None
        msg = json.loads(payload)
        if msg.get("type") != "pong":
            raise RuntimeError(f"expected pong, got {msg.get('type')}")
        print(connection_status("ping", "received pong response"))
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
        print(connection_status("idle", f"waiting up to {total_wait:.0f}s for server timeout..."))
        try:
            await asyncio.wait_for(ws.recv(), timeout=total_wait)
            raise RuntimeError("server sent data before idle close")
        except asyncio.TimeoutError:
            raise RuntimeError(
                f"server did not close within {total_wait:.0f}s "
                f"(expected idle timeout: {expect_seconds:.0f}s)"
            ) from None
        except websockets.ConnectionClosed as exc:
            print(connection_status("idle", f"server closed (code={exc.code} reason={exc.reason})"))


async def run_idle_suite(
    ws_url: str,
    *,
    normal_wait_s: float,
    idle_expect_s: float,
    idle_grace_s: float,
) -> bool:
    """Run the idle timeout and connection lifecycle scenarios sequentially."""

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

    print(f"\n{section_header('IDLE TESTS')}\n")
    
    success = True
    passed = 0
    failed = 0
    
    for label, factory in tests:
        print(connection_test_header(label))
        try:
            await factory()
            print(connection_pass(label))
            passed += 1
        except Exception as exc:  # noqa: BLE001
            success = False
            failed += 1
            print(connection_fail(label, str(exc)))
    
    # Summary
    print(f"\n{dim('─' * 40)}")
    if success:
        print(f"  All {passed} tests passed")
    else:
        print(f"  {passed} passed, {failed} failed")
    
    return success


__all__ = ["run_idle_suite"]
