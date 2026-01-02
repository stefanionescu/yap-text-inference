"""WebSocket message parsing and dispatch utilities.

This module provides helpers for parsing JSON messages from WebSocket frames
and dispatching them to type-specific handlers. It supports both sync and
async handler functions and gracefully handles malformed JSON.
"""

from __future__ import annotations

import inspect
import json
from typing import Any
from collections.abc import Awaitable, Callable, Mapping

from tests.helpers.errors import MessageParseError
from .ws import recv_raw


def parse_message(raw: str) -> dict[str, Any]:
    """Parse a raw WebSocket frame into a JSON dict."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MessageParseError(f"Invalid JSON frame: {raw!r}") from exc


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
    handler = handlers.get(msg.get("type"), default)
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

