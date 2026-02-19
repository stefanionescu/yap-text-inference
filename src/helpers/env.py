"""Environment variable parsing helpers.

Provides typed accessors for reading environment variables with defaults.
"""

from __future__ import annotations

import os


def env_flag(name: str, default: bool) -> bool:
    """Return True/False for typical truthy env encodings."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "off", "no", ""}


def env_int(name: str, default: int) -> int:
    """Parse an integer from an env var, returning *default* on missing/invalid."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def env_float(name: str, default: float) -> float:
    """Parse a float from an env var, returning *default* on missing/invalid."""
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def env_int_or_none(name: str, default: int | None = None) -> int | None:
    """Parse an int from env var; treat empty string as missing."""
    val = os.getenv(name, "")
    if not val:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def env_str(name: str, default: str) -> str:
    """Get a string from env var; treat empty string as missing."""
    val = os.getenv(name, "")
    return val if val else default


__all__ = [
    "env_flag",
    "env_float",
    "env_int",
    "env_int_or_none",
    "env_str",
]
