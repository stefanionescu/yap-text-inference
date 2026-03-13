"""WebSocket connection utilities for test clients.

This module provides helpers for WebSocket URL manipulation, connection
retry logic, and common protocol operations like sending the end frame.
It normalizes URLs to ensure consistent path handling across all test scripts.
"""

from __future__ import annotations

import os
import json
import asyncio
import inspect
import contextlib
from tests.config import DEFAULT_WS_PATH
from urllib.parse import urlsplit, urlunsplit
from collections.abc import Callable, Awaitable
from src.config.websocket import WS_PROTOCOL_VERSION

_HTTP_TO_WS = {"http": "ws", "https": "wss"}


def _ensure_path_and_scheme(url: str, default_path: str) -> tuple[str, str, str, str, str]:
    """Parse and normalize a WebSocket URL."""
    parts = urlsplit(url)
    scheme = parts.scheme or "ws"
    netloc = parts.netloc
    path = parts.path or ""

    # Handle inputs like "localhost:8000" (missing scheme)
    if not netloc and parts.path and ":" in parts.path:
        netloc = parts.path
        path = ""

    scheme = _HTTP_TO_WS.get(scheme, scheme)

    normalized_path = path
    if not normalized_path or normalized_path.strip("/") == "":
        normalized_path = default_path if default_path.startswith("/") else f"/{default_path}"

    return scheme, netloc, normalized_path, parts.query, parts.fragment


def _resolve_api_key(
    api_key_env: str = "TEXT_API_KEY",
    default_key: str | None = None,
    *,
    api_key: str | None = None,
) -> str:
    resolved_key = api_key or os.getenv(api_key_env) or default_key
    if not resolved_key:
        raise ValueError(f"{api_key_env} environment variable is required and must be set")
    return resolved_key


def with_api_key(
    url: str,
    api_key_env: str = "TEXT_API_KEY",
    default_key: str | None = None,
    *,
    api_key: str | None = None,
    default_path: str = DEFAULT_WS_PATH,
) -> str:
    """Normalize a WebSocket URL after validating API key presence.

    Authentication uses the `X-API-Key` header; this helper only validates auth
    availability and normalizes the URL shape.
    """
    _resolve_api_key(api_key_env, default_key, api_key=api_key)

    scheme, netloc, path, query, fragment = _ensure_path_and_scheme(url, default_path)
    if not netloc:
        raise ValueError(f"Invalid WebSocket URL '{url}'. Expected format ws(s)://host[:port][{default_path}]")
    return urlunsplit((scheme, netloc, path, query, fragment))


def build_api_key_headers(
    api_key_env: str = "TEXT_API_KEY",
    default_key: str | None = None,
    *,
    api_key: str | None = None,
) -> dict[str, str]:
    """Build auth headers for websocket connections."""
    resolved_key = _resolve_api_key(api_key_env, default_key, api_key=api_key)
    return {"X-API-Key": resolved_key}


async def send_client_end(ws) -> None:
    """Best-effort end signal to gracefully close the connection."""
    with contextlib.suppress(Exception):
        await ws.send(json.dumps({"type": "end", "v": WS_PROTOCOL_VERSION}))


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
    receive_result = receiver()
    if inspect.isawaitable(receive_result):
        if timeout is None:
            return await receive_result
        return await asyncio.wait_for(receive_result, timeout)
    return receive_result


@contextlib.asynccontextmanager
async def connect_with_retries(
    factory: Callable[[], contextlib.AbstractAsyncContextManager],
    *,
    max_retries: int = 2,
    base_delay_s: float = 0.5,
    backoff_factor: float = 2.0,
):
    """
    Attempt to open a websocket-like connection, retrying with exponential backoff.

    Retries `max_retries` times after the initial attempt, so the total attempts
    equal `max_retries + 1`. The `factory` must return a fresh async context
    manager each time (e.g., `lambda: websockets.connect(...)`).
    """

    attempt = 0
    delay = base_delay_s
    while True:
        connected = False
        try:
            async with factory() as ws:
                connected = True
                yield ws
                return
        except Exception:
            if connected:
                raise
            if attempt >= max_retries:
                raise
            await asyncio.sleep(max(0.0, delay))
            delay *= backoff_factor
            attempt += 1


__all__ = ["with_api_key", "build_api_key_headers", "send_client_end", "recv_raw", "connect_with_retries"]
