from __future__ import annotations

import asyncio
import contextlib
import json
import os
from typing import Awaitable, Callable

try:
    from config import DEFAULT_TEXT_API_KEY
except ModuleNotFoundError:
    from test.config import DEFAULT_TEXT_API_KEY

__all__ = ["with_api_key", "send_client_end", "recv_raw"]


def with_api_key(url: str, api_key_env: str = "TEXT_API_KEY", default_key: str = DEFAULT_TEXT_API_KEY) -> str:
    """Append API key as a query parameter to the WebSocket URL.

    This keeps client code consistent across tools; it does not validate the key.
    """
    api_key = os.getenv(api_key_env, default_key)
    return f"{url}&api_key={api_key}" if "?" in url else f"{url}?api_key={api_key}"


async def send_client_end(ws) -> None:
    """Best-effort `{"type": "end"}` signal to gracefully close sessions."""
    with contextlib.suppress(Exception):
        await ws.send(json.dumps({"type": "end"}))


def _resolve_recv(ws) -> Callable[[], Awaitable[str]]:
    """
    Support both `websockets` (recv) and Starlette/WebSocketTestClient (receive).
    """
    if hasattr(ws, "receive"):
        return ws.receive
    return ws.recv


async def recv_raw(ws, *, timeout: float | None = None) -> str:
    """Receive a single raw frame from a websocket-like object."""
    receiver = _resolve_recv(ws)
    if timeout is None:
        return await receiver()
    return await asyncio.wait_for(receiver(), timeout)

