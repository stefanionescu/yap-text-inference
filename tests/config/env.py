"""Environment-based configuration for test utilities.

This module reads test configuration from environment variables and provides
sensible defaults. It includes WebSocket connection settings, timeout values,
and rate-limiting parameters used across all test clients.
"""

from __future__ import annotations

import os


def get_int_env(key: str, fallback: int) -> int:
    """Read an integer from an environment variable with a fallback."""
    raw = os.getenv(key)
    if raw is None:
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def get_float_env(key: str, fallback: float) -> float:
    """Read a float from an environment variable with a fallback."""
    raw = os.getenv(key)
    if raw is None:
        return fallback
    try:
        return float(raw)
    except ValueError:
        return fallback


DEFAULT_SERVER_WS_URL = os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws")
DEFAULT_GENDER = os.getenv("GENDER", "female")
DEFAULT_PERSONALITY = os.getenv("PERSONALITY", "flirty")
DEFAULT_RECV_TIMEOUT_SEC = float(os.getenv("RECV_TIMEOUT_SEC", "60"))
DEFAULT_WS_PING_INTERVAL = int(os.getenv("TEST_WS_PING_INTERVAL", "20"))
DEFAULT_WS_PING_TIMEOUT = int(os.getenv("TEST_WS_PING_TIMEOUT", "20"))
POST_TOOL_IDLE_MIN_S = float(os.getenv("POST_TOOL_IDLE_MIN_S", "15"))
TOOL_WS_MESSAGE_WINDOW_SECONDS = float(os.getenv("TOOL_WS_MESSAGE_WINDOW_SECONDS", "60"))
TOOL_WS_MAX_MESSAGES_PER_WINDOW = int(os.getenv("TOOL_WS_MAX_MESSAGES_PER_WINDOW", "25"))

__all__ = [
    "DEFAULT_SERVER_WS_URL",
    "DEFAULT_GENDER",
    "DEFAULT_PERSONALITY",
    "DEFAULT_RECV_TIMEOUT_SEC",
    "DEFAULT_WS_PING_INTERVAL",
    "DEFAULT_WS_PING_TIMEOUT",
    "POST_TOOL_IDLE_MIN_S",
    "TOOL_WS_MESSAGE_WINDOW_SECONDS",
    "TOOL_WS_MAX_MESSAGES_PER_WINDOW",
    "get_int_env",
    "get_float_env",
]
