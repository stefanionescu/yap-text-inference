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
WS_WATCHDOG_TICK_S = float(os.getenv("WS_WATCHDOG_TICK_S", "5"))  # Check every 5s
WS_HANDSHAKE_ACQUIRE_TIMEOUT_S = float(os.getenv("WS_HANDSHAKE_ACQUIRE_TIMEOUT_S", "0.5"))

# ============================================================================
# WebSocket Close Codes
# ============================================================================
# These follow RFC 6455 conventions where possible.

WS_CLOSE_UNAUTHORIZED_CODE = int(os.getenv("WS_CLOSE_UNAUTHORIZED_CODE", "1008"))  # Policy violation
WS_CLOSE_BUSY_CODE = int(os.getenv("WS_CLOSE_BUSY_CODE", "1013"))  # Try again later
WS_CLOSE_IDLE_CODE = int(os.getenv("WS_CLOSE_IDLE_CODE", "4000"))  # Application-defined
WS_CLOSE_IDLE_REASON = os.getenv("WS_CLOSE_IDLE_REASON", "idle_timeout")
WS_CLOSE_CLIENT_REQUEST_CODE = int(os.getenv("WS_CLOSE_CLIENT_REQUEST_CODE", "1000"))  # Normal

# ============================================================================
# Message Envelope Keys (all WebSocket JSON messages)
# ============================================================================

WS_KEY_TYPE = "type"
WS_KEY_SESSION_ID = "session_id"
WS_KEY_REQUEST_ID = "request_id"
WS_KEY_PAYLOAD = "payload"

WS_UNKNOWN_SESSION_ID = "unknown"
WS_UNKNOWN_REQUEST_ID = "unknown"

# ============================================================================
# Message Types
# ============================================================================

WS_TYPE_START = "start"
WS_TYPE_CANCEL = "cancel"
WS_TYPE_FOLLOWUP = "followup"
WS_TYPE_PING = "ping"
WS_TYPE_PONG = "pong"
WS_TYPE_END = "end"
WS_TYPE_ACK = "ack"
WS_TYPE_ERROR = "error"
WS_TYPE_TOKEN = "token"
WS_TYPE_FINAL = "final"
WS_TYPE_DONE = "done"
WS_TYPE_STATUS = "status"
WS_TYPE_TOOLCALL = "toolcall"
WS_TYPE_CANCELLED = "cancelled"
WS_TYPE_SESSION_END = "session_end"

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

__all__ = [
    "WS_IDLE_TIMEOUT_S",
    "WS_WATCHDOG_TICK_S",
    "WS_HANDSHAKE_ACQUIRE_TIMEOUT_S",
    "WS_CLOSE_UNAUTHORIZED_CODE",
    "WS_CLOSE_BUSY_CODE",
    "WS_CLOSE_IDLE_CODE",
    "WS_CLOSE_IDLE_REASON",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    "WS_KEY_TYPE",
    "WS_KEY_SESSION_ID",
    "WS_KEY_REQUEST_ID",
    "WS_KEY_PAYLOAD",
    "WS_UNKNOWN_SESSION_ID",
    "WS_UNKNOWN_REQUEST_ID",
    "WS_TYPE_START",
    "WS_TYPE_CANCEL",
    "WS_TYPE_FOLLOWUP",
    "WS_TYPE_PING",
    "WS_TYPE_PONG",
    "WS_TYPE_END",
    "WS_TYPE_ACK",
    "WS_TYPE_ERROR",
    "WS_TYPE_TOKEN",
    "WS_TYPE_FINAL",
    "WS_TYPE_DONE",
    "WS_TYPE_STATUS",
    "WS_TYPE_TOOLCALL",
    "WS_TYPE_CANCELLED",
    "WS_TYPE_SESSION_END",
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
]
