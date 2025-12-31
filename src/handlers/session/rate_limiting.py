"""Rate limiting helpers for session chat prompt updates.

This module provides helper functions for managing rate limits on
chat prompt updates within a session. The rate limiter uses a sliding
window algorithm to prevent abuse while allowing legitimate usage.
"""

from __future__ import annotations

import time

from ..rate_limit import RateLimitError, SlidingWindowRateLimiter
from .state import SessionState


def get_chat_prompt_last_update_at(state: SessionState) -> float:
    """Get the timestamp of the last chat prompt update.
    
    Args:
        state: The session state to query.
        
    Returns:
        Monotonic timestamp of last update, or 0.0 if never updated.
    """
    return float(state.chat_prompt_last_update_at or 0.0)


def set_chat_prompt_last_update_at(state: SessionState, timestamp: float) -> None:
    """Set the timestamp of the last chat prompt update.
    
    Args:
        state: The session state to update.
        timestamp: Monotonic timestamp to record.
    """
    state.chat_prompt_last_update_at = timestamp


def consume_chat_prompt_update(
    state: SessionState,
    *,
    limit: int,
    window_seconds: float,
) -> float:
    """Record a chat prompt update attempt if within the rolling window limit.

    Creates or updates the rate limiter on the session state if the
    configuration has changed. Then attempts to consume a slot from
    the rate limiter.

    Args:
        state: The session state containing the rate limiter.
        limit: Maximum number of updates allowed in the window.
        window_seconds: Size of the sliding window in seconds.

    Returns:
        0.0 if the update was allowed, otherwise the number of seconds
        until the next slot frees up.
    """
    limiter = state.chat_prompt_rate_limiter
    if (
        limiter is None
        or limiter.limit != limit
        or limiter.window_seconds != window_seconds
    ):
        limiter = SlidingWindowRateLimiter(limit=limit, window_seconds=window_seconds)
        state.chat_prompt_rate_limiter = limiter

    try:
        limiter.consume()
    except RateLimitError as err:
        return err.retry_in

    state.chat_prompt_last_update_at = time.monotonic()
    return 0.0


__all__ = [
    "consume_chat_prompt_update",
    "get_chat_prompt_last_update_at",
    "set_chat_prompt_last_update_at",
]

