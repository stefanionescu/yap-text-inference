"""Math utilities for test utilities.

This module provides common mathematical helper functions used across
test scripts for formatting and rounding values.
"""

from __future__ import annotations


def round_ms(value: float | None, decimals: int = 2) -> float | None:
    """Round a millisecond value to the specified decimal places.
    
    Args:
        value: The value to round, or None.
        decimals: Number of decimal places (default 2).
    
    Returns:
        Rounded value, or None if input was None.
    """
    if value is None:
        return None
    return round(value, decimals)


def secs_to_ms(value: float | None) -> float | None:
    """Convert seconds to milliseconds.
    
    Args:
        value: Time in seconds, or None.
    
    Returns:
        Time in milliseconds, or None if input was None.
    """
    if value is None:
        return None
    return value * 1000.0


__all__ = ["round_ms", "secs_to_ms"]

