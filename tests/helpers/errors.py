"""Shared exception classes for test clients.

This module defines the error hierarchy for test WebSocket clients.
All test scripts should catch these errors and handle them appropriately
(exit with non-zero status codes, or display nicely for interactive sessions).

Error Hierarchy:
    TestClientError (base)
    ├── ServerError - Generic server error response
    │   ├── AuthenticationError - Invalid or missing API key
    │   ├── ServerAtCapacityError - Connection limit reached
    │   ├── RateLimitError - Too many requests (message or cancel)
    │   ├── ValidationError - Invalid field values or missing required fields
    │   ├── InvalidMessageError - Malformed JSON or unknown message type
    │   └── InternalServerError - Unexpected server error
    ├── ConnectionError - WebSocket connection issues
    │   ├── ConnectionClosedError - WebSocket closed unexpectedly
    │   ├── IdleTimeoutError - Server closed due to inactivity
    │   └── ConnectionRejectedError - Server rejected connection attempt
    ├── MessageParseError - Failed to parse WebSocket frame as JSON
    └── InputClosedError - stdin closed (EOF) or keyboard interrupt

Server Error Codes (from src/handlers/websocket/errors.py):
    - authentication_failed: Invalid or missing API key
    - server_at_capacity: Connection limit reached
    - missing_session_id: Start message lacks session_id
    - message_rate_limited: Too many messages per window
    - cancel_rate_limited: Too many cancel requests
    - invalid_message: Malformed JSON or missing type
    - unknown_message_type: Unrecognized message type
    - validation_error: Invalid field values
    - internal_error: Unexpected server error

WebSocket Close Codes:
    - 1000: Normal closure (client requested)
    - 1008: Policy violation (auth failure)
    - 1013: Try again later (server at capacity)
    - 4000: Idle timeout (server closed due to inactivity)
"""

from __future__ import annotations

from typing import Any


# ============================================================================
# Base Error Classes
# ============================================================================


class TestClientError(Exception):
    """Base class for all test client errors."""


# ============================================================================
# Server Error Classes
# ============================================================================


class ServerError(TestClientError):
    """Raised when the server returns an error message.
    
    Attributes:
        error_code: Machine-readable error code from server.
        message: Human-readable error description.
        extra: Additional fields from the error response.
    """

    # Map error_code -> specific exception class
    _SUBCLASS_MAP: dict[str, type[ServerError]] = {}

    def __init__(
        self,
        error_code: str,
        message: str,
        *,
        extra: dict[str, Any] | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.extra = extra or {}
        super().__init__(f"{error_code}: {message}")

    @classmethod
    def from_message(cls, msg: dict[str, Any]) -> ServerError:
        """Create an appropriate ServerError subclass from a server error message.
        
        Args:
            msg: The error message dict from the server.
            
        Returns:
            A ServerError instance (or appropriate subclass).
        """
        error_code = msg.get("error_code", "unknown")
        message = msg.get("message", str(msg))
        extra = {k: v for k, v in msg.items() if k not in ("type", "error_code", "message")}
        
        # Find matching subclass or use base ServerError
        error_class = cls._SUBCLASS_MAP.get(error_code, ServerError)
        return error_class(error_code, message, extra=extra)

    @property
    def retry_in(self) -> int | None:
        """Return retry delay in seconds if rate limited, else None."""
        return self.extra.get("retry_in")

    @property
    def friendly_message(self) -> str | None:
        """Return user-friendly message if provided by server."""
        return self.extra.get("friendly_message")

    def is_recoverable(self) -> bool:
        """Return True if this error can be recovered from by retrying.
        
        Recoverable errors are those where the client can simply wait
        and try again (e.g., rate limits, server busy).
        """
        return False

    def format_for_user(self) -> str:
        """Format the error for display to the user.
        
        Returns a user-friendly string that explains what went wrong
        and any suggested actions.
        """
        if self.friendly_message:
            return self.friendly_message
        return self.message


def _register_error_code(*codes: str):
    """Decorator to register error codes with their exception class."""
    def decorator(cls):
        for code in codes:
            ServerError._SUBCLASS_MAP[code] = cls
        return cls
    return decorator


@_register_error_code("authentication_failed")
class AuthenticationError(ServerError):
    """Raised when authentication fails (invalid or missing API key)."""

    def format_for_user(self) -> str:
        return (
            "Authentication failed. Please check your API key "
            "(--api-key or TEXT_API_KEY environment variable)."
        )


@_register_error_code("server_at_capacity")
class ServerAtCapacityError(ServerError):
    """Raised when the server is at maximum connection capacity."""

    def is_recoverable(self) -> bool:
        return True

    def format_for_user(self) -> str:
        return "Server is busy. Please try again later."


@_register_error_code("message_rate_limited", "cancel_rate_limited")
class RateLimitError(ServerError):
    """Raised when rate limit is exceeded.
    
    The `retry_in` property contains the number of seconds to wait
    before retrying. The `friendly_message` property may contain
    a user-friendly message from the server.
    """

    def is_recoverable(self) -> bool:
        return True

    def format_for_user(self) -> str:
        if self.friendly_message:
            return self.friendly_message
        retry = self.retry_in
        if retry:
            return f"Rate limited. Please wait {retry} second(s) before sending another message."
        return "Rate limited. Please slow down."


@_register_error_code("validation_error", "missing_session_id")
class ValidationError(ServerError):
    """Raised when the server rejects input due to validation failures."""


@_register_error_code("invalid_message", "unknown_message_type")
class InvalidMessageError(ServerError):
    """Raised when the server receives a malformed or unknown message."""


@_register_error_code("internal_error")
class InternalServerError(ServerError):
    """Raised when an unexpected server error occurs."""

    def format_for_user(self) -> str:
        return "An unexpected server error occurred. Please try again."


# ============================================================================
# Connection Error Classes
# ============================================================================


class ConnectionError(TestClientError):
    """Base class for WebSocket connection issues."""


class ConnectionClosedError(ConnectionError):
    """Raised when the WebSocket connection closes unexpectedly.
    
    Attributes:
        close_code: WebSocket close code if available.
        close_reason: Close reason string if available.
    """

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


class IdleTimeoutError(ConnectionClosedError):
    """Raised when the server closes the connection due to inactivity.
    
    This occurs when the connection has been idle for too long
    (typically 2.5 minutes by default). The client should reconnect
    if it wants to continue the conversation.
    """

    def __init__(
        self,
        message: str = "Connection closed due to inactivity",
        *,
        close_code: int | None = 4000,
        close_reason: str | None = "idle_timeout",
    ):
        super().__init__(message, close_code=close_code, close_reason=close_reason)


class ConnectionRejectedError(ConnectionError):
    """Raised when the server rejects a connection attempt.
    
    This can happen due to authentication failure or server at capacity.
    The embedded `server_error` contains the specific reason.
    """

    def __init__(self, server_error: ServerError):
        self.server_error = server_error
        super().__init__(f"Connection rejected: {server_error}")


# ============================================================================
# Message Parsing Errors
# ============================================================================


class MessageParseError(TestClientError):
    """Raised when a WebSocket frame cannot be parsed into JSON."""


# ============================================================================
# Input Errors
# ============================================================================


class InputClosedError(TestClientError):
    """Raised when stdin closes (EOF) or user presses Ctrl+C."""


# ============================================================================
# Utility Functions
# ============================================================================


def is_idle_timeout_close(close_code: int | None, close_reason: str | None) -> bool:
    """Check if a WebSocket close represents an idle timeout.
    
    Args:
        close_code: The WebSocket close code.
        close_reason: The close reason string.
        
    Returns:
        True if this close was due to idle timeout.
    """
    if close_code == 4000:
        return True
    if close_reason and "idle" in close_reason.lower():
        return True
    return False


def error_from_close(
    close_code: int | None,
    close_reason: str | None,
) -> ConnectionClosedError:
    """Create an appropriate ConnectionClosedError from close code/reason.
    
    Args:
        close_code: The WebSocket close code.
        close_reason: The close reason string.
        
    Returns:
        IdleTimeoutError if this was an idle timeout, else ConnectionClosedError.
    """
    if is_idle_timeout_close(close_code, close_reason):
        return IdleTimeoutError(close_code=close_code, close_reason=close_reason)
    return ConnectionClosedError(
        close_code=close_code,
        close_reason=close_reason,
    )


__all__ = [
    # Base
    "TestClientError",
    # Server errors
    "ServerError",
    "AuthenticationError",
    "ServerAtCapacityError",
    "RateLimitError",
    "ValidationError",
    "InvalidMessageError",
    "InternalServerError",
    # Connection errors
    "ConnectionError",
    "ConnectionClosedError",
    "IdleTimeoutError",
    "ConnectionRejectedError",
    # Other errors
    "MessageParseError",
    "InputClosedError",
    # Utilities
    "is_idle_timeout_close",
    "error_from_close",
]
