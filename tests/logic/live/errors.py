"""Exception classes for live interactive sessions.

This module re-exports error types from the shared errors module
and provides aliases for backwards compatibility. All exceptions
inherit from TestClientError (via the shared module).

For new code, prefer importing directly from tests.helpers.errors.
"""

from __future__ import annotations

from tests.helpers.errors import (
    # Re-export with live-specific aliases for backwards compatibility
    ConnectionClosedError,
    IdleTimeoutError,
    InputClosedError,
    RateLimitError,
    ServerError,
    TestClientError,
    error_from_close,
    is_idle_timeout_close,
)

# Aliases for backwards compatibility with existing live test code
LiveClientError = TestClientError
LiveConnectionClosed = ConnectionClosedError
LiveServerError = ServerError
LiveInputClosed = InputClosedError
LiveRateLimitError = RateLimitError
LiveIdleTimeout = IdleTimeoutError

__all__ = [
    # Aliases (backwards compat)
    "LiveClientError",
    "LiveConnectionClosed",
    "LiveServerError",
    "LiveInputClosed",
    "LiveRateLimitError",
    "LiveIdleTimeout",
    # Utilities
    "error_from_close",
    "is_idle_timeout_close",
]
