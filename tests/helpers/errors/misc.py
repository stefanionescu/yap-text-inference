"""Miscellaneous helper error types."""

from __future__ import annotations

from typing import Any

from .base import TestClientError


class MessageParseError(TestClientError):
    """Raised when a WebSocket frame cannot be parsed into JSON."""


class InputClosedError(TestClientError):
    """Raised when stdin closes (EOF) or user presses Ctrl+C."""


class StreamError(TestClientError):
    """Raised when stream consumption encounters a server error."""

    def __init__(self, message: dict[str, Any]) -> None:
        self.message = message
        super().__init__(str(message))


class PromptSelectionError(ValueError):
    """Raised when prompt selection fails due to invalid parameters."""


__all__ = [
    "MessageParseError",
    "InputClosedError",
    "StreamError",
    "PromptSelectionError",
]
