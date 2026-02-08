"""Error hierarchy used across test helpers.

This package groups server, connection, and client-side error types so callers
can continue importing them from `tests.helpers.errors` while we keep the
implementation modular.
"""

from .base import TestClientError
from .misc import StreamError, InputClosedError, MessageParseError, PromptSelectionError
from .server import (
    ServerError,
    RateLimitError,
    ValidationError,
    AuthenticationError,
    InternalServerError,
    InvalidMessageError,
    ServerAtCapacityError,
)
from .connection import ConnectionError, IdleTimeoutError, ConnectionClosedError, ConnectionRejectedError

__all__ = [
    "TestClientError",
    "ServerError",
    "AuthenticationError",
    "ServerAtCapacityError",
    "RateLimitError",
    "ValidationError",
    "InvalidMessageError",
    "InternalServerError",
    "ConnectionError",
    "ConnectionClosedError",
    "IdleTimeoutError",
    "ConnectionRejectedError",
    "MessageParseError",
    "InputClosedError",
    "StreamError",
    "PromptSelectionError",
]
