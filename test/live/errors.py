from __future__ import annotations


class LiveClientError(RuntimeError):
    """Base class for live client issues."""


class LiveConnectionClosed(LiveClientError):
    """Raised when the websocket closes unexpectedly."""


class LiveServerError(LiveClientError):
    """Raised on structured server error frames."""


class LiveInputClosed(LiveClientError):
    """Raised when stdin closes (EOF)."""


__all__ = [
    "LiveClientError",
    "LiveConnectionClosed",
    "LiveServerError",
    "LiveInputClosed",
]


