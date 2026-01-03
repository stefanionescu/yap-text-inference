"""Error hierarchy used across test helpers.

This package groups server, connection, and client-side error types so callers
can continue importing them from `tests.helpers.errors` while we keep the
implementation modular.
"""

from .base import TestClientError
from .connection import (
    ConnectionClosedError,
    ConnectionError,
    ConnectionRejectedError,
    IdleTimeoutError,
)
from .misc import InputClosedError, MessageParseError, PromptSelectionError, StreamError
from .server import (
    AuthenticationError,
    InvalidMessageError,
    InternalServerError,
    RateLimitError,
    ServerAtCapacityError,
    ServerError,
    ValidationError,
)

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


