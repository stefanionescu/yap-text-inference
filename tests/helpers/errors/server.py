"""Server-originated error types."""

from __future__ import annotations

from typing import Any

from .base import TestClientError


class ServerError(TestClientError):
    """Raised when the server returns an error message."""

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
        """Create an appropriate ServerError subclass from a server error message."""
        payload: dict[str, Any] = {}
        payload_raw = msg.get("payload")
        if isinstance(payload_raw, dict):
            payload = payload_raw
        error_code = msg.get("code") or payload.get("code") or msg.get("error_code", "unknown")
        message = msg.get("message") or payload.get("message") or str(msg)
        extra = {
            k: v for k, v in msg.items() if k not in ("type", "error_code", "code", "message", "payload", "details")
        }
        details = payload.get("details") or msg.get("details")
        if isinstance(details, dict):
            extra.update(details)
        error_class = cls._SUBCLASS_MAP.get(error_code, ServerError)
        return error_class(error_code, message, extra=extra)

    @property
    def retry_in(self) -> int | None:
        return self.extra.get("retry_in")

    @property
    def friendly_message(self) -> str | None:
        return self.extra.get("friendly_message")

    def is_recoverable(self) -> bool:
        return False

    def format_for_user(self) -> str:
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
        return "Authentication failed. Please check your API key (--api-key or TEXT_API_KEY environment variable)."


@_register_error_code("server_at_capacity")
class ServerAtCapacityError(ServerError):
    """Raised when the server is at maximum connection capacity."""

    def is_recoverable(self) -> bool:
        return True

    def format_for_user(self) -> str:
        return "Server is busy. Please try again later."


@_register_error_code("rate_limited", "message_rate_limited", "cancel_rate_limited")
class RateLimitError(ServerError):
    """Raised when rate limits are exceeded."""

    def is_recoverable(self) -> bool:
        return True

    def format_for_user(self) -> str:
        if self.friendly_message:
            return self.friendly_message
        retry = self.retry_in
        if retry:
            return f"Rate limited. Please wait {retry} second(s) before sending another message."
        return "Rate limited. Please slow down."


@_register_error_code("invalid_payload", "invalid_settings", "validation_error", "missing_session_id")
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


__all__ = [
    "ServerError",
    "AuthenticationError",
    "ServerAtCapacityError",
    "RateLimitError",
    "ValidationError",
    "InvalidMessageError",
    "InternalServerError",
]
