"""WebSocket connection error types."""

from __future__ import annotations

from tests.config.defaults import WS_IDLE_CLOSE_CODE, WS_IDLE_CLOSE_REASON

from .server import ServerError
from .base import TestClientError


class ConnectionError(TestClientError):
    """Base class for WebSocket connection issues."""


class ConnectionClosedError(ConnectionError):
    """Raised when the WebSocket connection closes unexpectedly."""

    def __init__(
        self,
        message: str = "WebSocket connection closed",
        *,
        close_code: int | None = None,
        close_reason: str | None = None,
    ):
        self.close_code = close_code
        self.close_reason = close_reason
        parts = [message]
        if close_code is not None:
            parts.append(f"code={close_code}")
        if close_reason:
            parts.append(f"reason={close_reason}")
        super().__init__(" ".join(parts))

    @classmethod
    def from_close(
        cls,
        close_code: int | None,
        close_reason: str | None,
    ) -> ConnectionClosedError:
        if IdleTimeoutError.matches(close_code, close_reason):
            return IdleTimeoutError(close_code=close_code, close_reason=close_reason)
        return cls(close_code=close_code, close_reason=close_reason)


class IdleTimeoutError(ConnectionClosedError):
    """Raised when the server closes the connection due to inactivity."""

    def __init__(
        self,
        message: str = "Connection closed due to inactivity",
        *,
        close_code: int | None = WS_IDLE_CLOSE_CODE,
        close_reason: str | None = WS_IDLE_CLOSE_REASON,
    ):
        super().__init__(message, close_code=close_code, close_reason=close_reason)

    @staticmethod
    def matches(close_code: int | None, close_reason: str | None) -> bool:
        if close_code == WS_IDLE_CLOSE_CODE:
            return True
        if close_reason is None:
            return False
        return "idle" in close_reason.lower()


class ConnectionRejectedError(ConnectionError):
    """Raised when the server rejects a connection attempt."""

    def __init__(self, server_error: ServerError):
        self.server_error = server_error
        super().__init__(f"Connection rejected: {server_error}")


__all__ = [
    "ConnectionError",
    "ConnectionClosedError",
    "IdleTimeoutError",
    "ConnectionRejectedError",
]
