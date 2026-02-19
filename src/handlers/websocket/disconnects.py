"""Helpers for classifying expected WebSocket disconnect exceptions."""

from __future__ import annotations

from fastapi import WebSocketDisconnect

try:  # pragma: no cover - availability depends on runtime backend
    from anyio import EndOfStream, BrokenResourceError, ClosedResourceError
except Exception:  # noqa: BLE001
    BrokenResourceError = ClosedResourceError = EndOfStream = None  # type: ignore[assignment]

try:  # pragma: no cover - availability depends on runtime backend
    from websockets.exceptions import ConnectionClosed
except Exception:  # noqa: BLE001
    ConnectionClosed = None  # type: ignore[assignment]

_runtime_errors: list[type[BaseException]] = [
    ConnectionResetError,
    BrokenPipeError,
    EOFError,
]
for maybe_type in (BrokenResourceError, ClosedResourceError, EndOfStream):
    if isinstance(maybe_type, type):
        _runtime_errors.append(maybe_type)
_RUNTIME_DISCONNECT_ERRORS = tuple(_runtime_errors)

_RUNTIME_DISCONNECT_MESSAGES = (
    "websocket is not connected",
    "cannot call receive once a disconnect message has been received",
)


def is_expected_disconnect(exc: BaseException) -> bool:
    """Return True when the exception represents normal transport teardown."""

    if isinstance(exc, WebSocketDisconnect):
        return True
    if isinstance(ConnectionClosed, type) and isinstance(exc, ConnectionClosed):
        return True
    if isinstance(exc, _RUNTIME_DISCONNECT_ERRORS):
        return True
    if isinstance(exc, RuntimeError):
        message = str(exc).strip().lower()
        return any(fragment in message for fragment in _RUNTIME_DISCONNECT_MESSAGES)
    return False


__all__ = ["is_expected_disconnect"]
