"""WebSocket message parsing and dispatch utilities.

This module provides helpers for parsing JSON messages from WebSocket frames
and dispatching them to type-specific handlers. It supports both sync and
async handler functions and gracefully handles malformed JSON.
"""

from __future__ import annotations

import json
import inspect
from typing import Any
from .ws import recv_raw
from .payloads import build_message_payload
from collections.abc import Mapping, Callable, Awaitable
from tests.support.helpers.errors import StreamError, MessageParseError


def parse_message(raw: str) -> dict[str, Any]:
    """Parse a raw WebSocket frame into a JSON dict."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MessageParseError(f"Invalid JSON frame: {raw!r}") from exc
    if not isinstance(msg, dict):
        return msg
    return msg


async def iter_messages(ws, *, timeout: float | None = None, ignore_invalid: bool = True):
    """
    Yield parsed JSON messages from a websocket connection.

    Args:
        ws: WebSocket connection (websockets client or Starlette test client).
        timeout: Optional timeout applied to each recv call.
        ignore_invalid: If True, silently skip malformed frames.
    """
    while True:
        raw = await recv_raw(ws, timeout=timeout)
        try:
            yield parse_message(raw)
        except MessageParseError:
            if ignore_invalid:
                continue
            raise


async def _send_json_frame(ws, payload: dict[str, Any]) -> None:
    raw = json.dumps(payload)
    if hasattr(ws, "send_text"):
        result = ws.send_text(raw)
    elif hasattr(ws, "send"):
        result = ws.send(raw)
    else:
        raise TypeError("websocket-like object must expose send_text() or send()")
    if inspect.isawaitable(result):
        await result


async def bootstrap_session(
    ws,
    start_payload: dict[str, Any],
    *,
    timeout: float | None = None,
) -> None:
    """Send a bootstrap-only start payload and wait for the terminal done frame."""
    await _send_json_frame(ws, start_payload)
    async for msg in iter_messages(ws, timeout=timeout):
        msg_type = msg.get("type")
        if msg_type == "done":
            return
        if msg_type == "error":
            raise StreamError(msg)
        raise RuntimeError(f"Unexpected websocket frame during bootstrap: {msg!r}")
    raise RuntimeError("WebSocket closed before bootstrap completed")


async def send_initial_user_turn(
    ws,
    start_payload: dict[str, Any],
    user_text: str,
    *,
    sampling: dict[str, float | int] | None = None,
    timeout: float | None = None,
) -> None:
    """Bootstrap a session, then send the first real user message."""
    await bootstrap_session(ws, start_payload, timeout=timeout)
    await _send_json_frame(
        ws,
        build_message_payload(user_text, sampling=sampling),
    )


async def dispatch_message(
    msg: dict[str, Any],
    handlers: Mapping[str, Callable[[dict[str, Any]], Awaitable[Any] | Any]],
    *,
    default: Callable[[dict[str, Any]], Awaitable[Any] | Any] | None = None,
) -> Any:
    """
    Dispatch a websocket message to a handler based on its `type` field.

    Handlers can be synchronous or asynchronous callables.
    """
    message_type = msg.get("type")
    handler = handlers.get(message_type) if isinstance(message_type, str) else None
    if handler is None:
        handler = default
    if handler is None:
        return None

    result = handler(msg)
    if inspect.isawaitable(result):
        return await result
    return result


__all__ = [
    "bootstrap_session",
    "MessageParseError",
    "dispatch_message",
    "iter_messages",
    "parse_message",
    "send_initial_user_turn",
]
