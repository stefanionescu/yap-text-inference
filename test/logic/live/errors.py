from __future__ import annotations


class LiveClientError(RuntimeError):
    """Base class for live client issues."""


class LiveConnectionClosed(LiveClientError):
    """Raised when the websocket closes unexpectedly."""


class LiveServerError(LiveClientError):
    """Raised on structured server error frames."""

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.code = code


class LiveInputClosed(LiveClientError):
    """Raised when stdin closes (EOF)."""


__all__ = [
    "LiveClientError",
    "LiveConnectionClosed",
    "LiveServerError",
    "LiveInputClosed",
]


