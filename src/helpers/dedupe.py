"""Centralized warning tracking for inference engines.

This module provides a simple way to track which warnings have been emitted
to avoid spamming logs with repeated warnings.

Usage:
    from src.helpers.dedupe import warn_once

    warn_once("cuda_mem", "torch unavailable for CUDA mem introspection")
    warn_once("cuda_mem", "same warning")  # Suppressed
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Set of warning keys that have been emitted
_emitted_warnings: set[str] = set()


def warn_once(key: str, message: str, *, prefix: str = "[config]") -> bool:
    """Emit a warning message only once per key.

    Args:
        key: Unique identifier for this warning type.
        message: The warning message to print.
        prefix: Optional prefix for the message.

    Returns:
        True if the warning was emitted, False if already emitted.
    """
    if key in _emitted_warnings:
        return False

    _emitted_warnings.add(key)
    full_message = f"{prefix} Warning: {message}" if prefix else f"Warning: {message}"
    logger.warning(full_message)
    return True


def info_once(key: str, message: str, *, prefix: str = "[config]") -> bool:
    """Emit an info message only once per key.

    Args:
        key: Unique identifier for this message type.
        message: The info message to print.
        prefix: Optional prefix for the message.

    Returns:
        True if the message was emitted, False if already emitted.
    """
    if key in _emitted_warnings:
        return False

    _emitted_warnings.add(key)
    full_message = f"{prefix} {message}" if prefix else message
    logger.info(full_message)
    return True


def has_warned(key: str) -> bool:
    """Check if a warning has been emitted for the given key."""
    return key in _emitted_warnings


def reset_warnings() -> None:
    """Clear all emitted warnings. Useful for testing."""
    _emitted_warnings.clear()


__all__ = ["warn_once", "info_once", "has_warned", "reset_warnings"]
