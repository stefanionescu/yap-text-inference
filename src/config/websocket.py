"""WebSocket-specific runtime configuration values.

This module defines constants for WebSocket connection lifecycle management:

Timeouts:
    WS_IDLE_TIMEOUT_S: Close connections after this many seconds of inactivity.
        This prevents resource leaks from abandoned connections.

    WS_WATCHDOG_TICK_S: How often the idle watchdog checks activity.
        Lower values = more responsive timeout, higher CPU usage.

    WS_HANDSHAKE_ACQUIRE_TIMEOUT_S: Max time to wait for connection slot.
        If the server is at capacity, connections wait this long before
        being rejected.

Close Codes (RFC 6455):
    1000: Normal closure (client requested)
    1008: Policy violation (auth failure)
    1013: Try again later (server at capacity)
    4000+: Application-defined (idle timeout)

Environment Variables:
    All values can be overridden. The defaults provide a balance between
    responsiveness and resource efficiency.
"""

from __future__ import annotations

import os

# ============================================================================
# Timeout Configuration
# ============================================================================

WS_IDLE_TIMEOUT_S = float(os.getenv("WS_IDLE_TIMEOUT_S", "150"))  # 2.5 minutes
WS_WATCHDOG_TICK_S = float(os.getenv("WS_WATCHDOG_TICK_S", "10"))  # Check every 10s
WS_HANDSHAKE_ACQUIRE_TIMEOUT_S = float(os.getenv("WS_HANDSHAKE_ACQUIRE_TIMEOUT_S", "0.5"))
WS_PROTOCOL_VERSION = int(os.getenv("WS_PROTOCOL_VERSION", "1"))
WS_MAX_MESSAGE_BYTES = int(os.getenv("WS_MAX_MESSAGE_BYTES", "65536"))
WS_HISTORY_MAX_ITEMS = int(os.getenv("WS_HISTORY_MAX_ITEMS", "200"))
WS_HISTORY_ITEM_MAX_CHARS = int(os.getenv("WS_HISTORY_ITEM_MAX_CHARS", "4000"))
WS_HISTORY_TOTAL_MAX_CHARS = int(os.getenv("WS_HISTORY_TOTAL_MAX_CHARS", "200000"))
WS_AUTH_WINDOW_SECONDS = float(os.getenv("WS_AUTH_WINDOW_SECONDS", "60"))
WS_MAX_AUTH_FAILURES_PER_WINDOW = int(os.getenv("WS_MAX_AUTH_FAILURES_PER_WINDOW", "20"))
_allowed_origins_raw = os.getenv("WS_ALLOWED_ORIGINS", "")
WS_ALLOWED_ORIGINS = tuple(origin.strip() for origin in _allowed_origins_raw.split(",") if origin.strip())

# ============================================================================
# WebSocket Close Codes
# ============================================================================
# These follow RFC 6455 conventions where possible.

WS_CLOSE_UNAUTHORIZED_CODE = 1008  # Policy violation
WS_CLOSE_BUSY_CODE = 1013  # Try again later
WS_CLOSE_IDLE_CODE = 4000  # Application-defined
WS_CLOSE_IDLE_REASON = "idle_timeout"
WS_CLOSE_CLIENT_REQUEST_CODE = 1000  # Normal

# Runtime fallback for framework-specific receive-after-disconnect edge cases.
WS_EXPECTED_DISCONNECT_RUNTIME_FRAGMENTS: tuple[str, ...] = (
    "websocket is not connected",
    "disconnect message has been received",
)

# ============================================================================
# Message Types
# ============================================================================

WS_TYPE_START = "start"
WS_TYPE_CANCEL = "cancel"
WS_TYPE_MESSAGE = "message"
WS_TYPE_PING = "ping"
WS_TYPE_PONG = "pong"
WS_TYPE_END = "end"
WS_TYPE_ERROR = "error"
WS_TYPE_TOKEN = "token"  # noqa: S105
WS_TYPE_FINAL = "final"
WS_TYPE_DONE = "done"
WS_TYPE_TOOL = "tool"
WS_TYPE_CANCELLED = "cancelled"

# ============================================================================
# Error Codes (payload "code" values)
# ============================================================================

WS_ERROR_AUTH_FAILED = "authentication_failed"
WS_ERROR_SERVER_BUSY = "server_at_capacity"
WS_ERROR_INVALID_MESSAGE = "invalid_message"
WS_ERROR_INVALID_PAYLOAD = "invalid_payload"
WS_ERROR_INVALID_SETTINGS = "invalid_settings"
WS_ERROR_RATE_LIMITED = "rate_limited"
WS_ERROR_QUEUE_FULL = "queue_full"
WS_ERROR_TEXT_TOO_LONG = "text_too_long"
WS_ERROR_INVALID_VOICE = "invalid_voice"
WS_ERROR_INTERNAL = "internal_error"

# ============================================================================
# HTTP-Style Status Codes
# ============================================================================

WS_STATUS_OK = 200
WS_STATUS_BAD_REQUEST = 400
WS_STATUS_UNAUTHORIZED = 401
WS_STATUS_RATE_LIMITED = 429
WS_STATUS_INTERNAL = 500
WS_STATUS_UNAVAILABLE = 503

# Mapping from error string codes to numeric status
ERROR_CODE_TO_STATUS: dict[str, int] = {
    WS_ERROR_AUTH_FAILED: WS_STATUS_UNAUTHORIZED,
    WS_ERROR_SERVER_BUSY: WS_STATUS_UNAVAILABLE,
    WS_ERROR_INVALID_MESSAGE: WS_STATUS_BAD_REQUEST,
    WS_ERROR_INVALID_PAYLOAD: WS_STATUS_BAD_REQUEST,
    WS_ERROR_INVALID_SETTINGS: WS_STATUS_BAD_REQUEST,
    WS_ERROR_RATE_LIMITED: WS_STATUS_RATE_LIMITED,
    WS_ERROR_QUEUE_FULL: WS_STATUS_UNAVAILABLE,
    WS_ERROR_TEXT_TOO_LONG: WS_STATUS_BAD_REQUEST,
    WS_ERROR_INVALID_VOICE: WS_STATUS_BAD_REQUEST,
    WS_ERROR_INTERNAL: WS_STATUS_INTERNAL,
}

__all__ = [
    "WS_IDLE_TIMEOUT_S",
    "WS_WATCHDOG_TICK_S",
    "WS_HANDSHAKE_ACQUIRE_TIMEOUT_S",
    "WS_PROTOCOL_VERSION",
    "WS_MAX_MESSAGE_BYTES",
    "WS_HISTORY_MAX_ITEMS",
    "WS_HISTORY_ITEM_MAX_CHARS",
    "WS_HISTORY_TOTAL_MAX_CHARS",
    "WS_AUTH_WINDOW_SECONDS",
    "WS_MAX_AUTH_FAILURES_PER_WINDOW",
    "WS_ALLOWED_ORIGINS",
    "WS_CLOSE_UNAUTHORIZED_CODE",
    "WS_CLOSE_BUSY_CODE",
    "WS_CLOSE_IDLE_CODE",
    "WS_CLOSE_IDLE_REASON",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    "WS_EXPECTED_DISCONNECT_RUNTIME_FRAGMENTS",
    "WS_TYPE_START",
    "WS_TYPE_CANCEL",
    "WS_TYPE_MESSAGE",
    "WS_TYPE_PING",
    "WS_TYPE_PONG",
    "WS_TYPE_END",
    "WS_TYPE_ERROR",
    "WS_TYPE_TOKEN",
    "WS_TYPE_FINAL",
    "WS_TYPE_DONE",
    "WS_TYPE_TOOL",
    "WS_TYPE_CANCELLED",
    "WS_ERROR_AUTH_FAILED",
    "WS_ERROR_SERVER_BUSY",
    "WS_ERROR_INVALID_MESSAGE",
    "WS_ERROR_INVALID_PAYLOAD",
    "WS_ERROR_INVALID_SETTINGS",
    "WS_ERROR_RATE_LIMITED",
    "WS_ERROR_QUEUE_FULL",
    "WS_ERROR_TEXT_TOO_LONG",
    "WS_ERROR_INVALID_VOICE",
    "WS_ERROR_INTERNAL",
    "WS_STATUS_OK",
    "WS_STATUS_BAD_REQUEST",
    "WS_STATUS_UNAUTHORIZED",
    "WS_STATUS_RATE_LIMITED",
    "WS_STATUS_INTERNAL",
    "WS_STATUS_UNAVAILABLE",
    "ERROR_CODE_TO_STATUS",
]
