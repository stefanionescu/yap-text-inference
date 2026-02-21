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
from tests.helpers.errors import MessageParseError
from collections.abc import Mapping, Callable, Awaitable


def parse_message(raw: str) -> dict[str, Any]:
    """Parse a raw WebSocket frame into a JSON dict."""
    try:
        msg = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MessageParseError(f"Invalid JSON frame: {raw!r}") from exc
    if isinstance(msg, dict):
        payload = msg.get("payload")
        if isinstance(payload, dict):
            # Flatten payload for test convenience while preserving envelope keys.
            merged = dict(msg)
            merged.update(payload)
            return merged
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
    "MessageParseError",
    "dispatch_message",
    "iter_messages",
    "parse_message",
]
