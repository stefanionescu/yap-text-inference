"""Environment variable parsing helpers for test utilities.

Provides typed accessors for reading configuration from environment variables
with fallback defaults. Used by test runners and config modules.
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


__all__ = [
    "get_int_env",
    "get_float_env",
]

