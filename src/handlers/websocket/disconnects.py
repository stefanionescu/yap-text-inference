"""Helpers for classifying expected WebSocket transport disconnects."""

from __future__ import annotations

from fastapi import WebSocketDisconnect
from websockets.exceptions import ConnectionClosed
from anyio import EndOfStream, BrokenResourceError, ClosedResourceError

from ...config.websocket import WS_EXPECTED_DISCONNECT_RUNTIME_FRAGMENTS

WS_EXPECTED_DISCONNECT_EXC_TYPES: tuple[type[BaseException], ...] = (
    WebSocketDisconnect,
    ConnectionClosed,
    ConnectionResetError,
    BrokenPipeError,
    EOFError,
    BrokenResourceError,
    ClosedResourceError,
    EndOfStream,
)


def is_expected_ws_disconnect(exc: BaseException) -> bool:
    """Return True when exception indicates expected transport disconnect."""

    if isinstance(exc, WS_EXPECTED_DISCONNECT_EXC_TYPES):
        return True
    if not isinstance(exc, RuntimeError):
        return False
    message = str(exc).strip().lower()
    return any(fragment in message for fragment in WS_EXPECTED_DISCONNECT_RUNTIME_FRAGMENTS)


__all__ = [
    "WS_EXPECTED_DISCONNECT_EXC_TYPES",
    "is_expected_ws_disconnect",
]
