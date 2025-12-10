from __future__ import annotations

import os


def env_flag(key: str, default: bool = False) -> bool:
    """Parse boolean env var (1/true/yes = True, 0/false/no = False)."""
    val = os.getenv(key, "").strip().lower()
    if not val:
        return default
    return val in ("1", "true", "yes", "on")


def get_int_env(key: str, fallback: int) -> int:
    raw = os.getenv(key)
    if raw is None:
        return fallback
    try:
        return int(raw)
    except ValueError:
        return fallback


def get_float_env(key: str, fallback: float) -> float:
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

# Classifier mode: when True, tool prompts are not required (server uses classifier model)
# Set via CLASSIFIER_MODE=1 or --classifier-mode CLI flag
CLASSIFIER_MODE = env_flag("CLASSIFIER_MODE", False)

__all__ = [
    "DEFAULT_SERVER_WS_URL",
    "DEFAULT_GENDER",
    "DEFAULT_PERSONALITY",
    "DEFAULT_RECV_TIMEOUT_SEC",
    "DEFAULT_WS_PING_INTERVAL",
    "DEFAULT_WS_PING_TIMEOUT",
    "POST_TOOL_IDLE_MIN_S",
    "CLASSIFIER_MODE",
    "env_flag",
    "get_int_env",
    "get_float_env",
]

