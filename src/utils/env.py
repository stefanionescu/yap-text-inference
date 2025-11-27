"""Environment helper utilities."""

from __future__ import annotations

import os


def env_flag(name: str, default: bool) -> bool:
    """Return True/False for typical truthy env encodings."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


__all__ = ["env_flag"]

