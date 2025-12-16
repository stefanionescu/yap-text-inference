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

Sentinel Values:
    Special string values that can be sent instead of JSON to trigger
    specific actions (cancel current request, end session).

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
# Sentinel Values
# ============================================================================
# Simple string messages that trigger specific actions without JSON parsing.

WS_END_SENTINEL = os.getenv("WS_END_SENTINEL", "__END__")  # Close session
WS_CANCEL_SENTINEL = os.getenv("WS_CANCEL_SENTINEL", "__CANCEL__")  # Cancel request

__all__ = [
    "WS_IDLE_TIMEOUT_S",
    "WS_WATCHDOG_TICK_S",
    "WS_HANDSHAKE_ACQUIRE_TIMEOUT_S",
    "WS_CLOSE_UNAUTHORIZED_CODE",
    "WS_CLOSE_BUSY_CODE",
    "WS_CLOSE_IDLE_CODE",
    "WS_CLOSE_IDLE_REASON",
    "WS_CLOSE_CLIENT_REQUEST_CODE",
    "WS_END_SENTINEL",
    "WS_CANCEL_SENTINEL",
]

