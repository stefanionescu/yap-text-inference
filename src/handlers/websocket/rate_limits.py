"""Rate limiting utilities for WebSocket message handling.

This module provides rate limit selection and consumption for different
message types:

- Regular messages: Limited to prevent spam
- Cancel messages: Separate bucket to prevent cancel bursts starving messages
- Control messages (ping/pong/end): Exempt from rate limiting
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING, Any

from .helpers import safe_send_json
from ...config.chat import MESSAGE_RATE_LIMIT_MESSAGES
from ..rate_limit import RateLimitError, SlidingWindowRateLimiter

if TYPE_CHECKING:
    from fastapi import WebSocket


def select_rate_limiter(
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> tuple[SlidingWindowRateLimiter | None, str]:
    """Pick which limiter applies to the message type (if any).

    Cancel messages receive their own bucket so a burst of cancel attempts
    cannot starve regular messaging. Control traffic (ping/pong/end) is
    exempt from rate checks because it is either connection liveness or
    teardown bookkeeping.
    
    Args:
        msg_type: The message type string.
        message_limiter: Rate limiter for regular messages.
        cancel_limiter: Rate limiter for cancel messages.
        
    Returns:
        Tuple of (limiter or None, label string for error messages).
    """
    if msg_type == "cancel":
        return cancel_limiter, "cancel"
    if msg_type in {"ping", "pong", "end"}:
        return None, ""
    return message_limiter, "message"


async def consume_limiter(
    ws: WebSocket,
    limiter: SlidingWindowRateLimiter,
    label: str,
) -> bool:
    """Attempt to consume a limiter token, sending an error on failure.
    
    Args:
        ws: WebSocket to send error on.
        limiter: The rate limiter to consume from.
        label: Label for error message ("message" or "cancel").
        
    Returns:
        True if consumption succeeded, False if rate limited.
    """
    try:
        limiter.consume()
    except RateLimitError as err:
        retry_in = int(max(1, math.ceil(err.retry_in))) if err.retry_in > 0 else 1
        limit_desc = limiter.limit
        window_desc = int(limiter.window_seconds)
        message = (
            f"{label} rate limit: at most {limit_desc} per {window_desc} seconds; "
            f"retry in {retry_in} seconds"
        )
        extra: dict[str, Any] = {"retry_in": retry_in}
        # Add friendly message only for message rate limits (not cancel)
        if label == "message":
            extra["friendly_message"] = random.choice(MESSAGE_RATE_LIMIT_MESSAGES)
        await safe_send_json(ws, {
            "type": "error",
            "error_code": f"{label}_rate_limited",
            "message": message,
            **extra,
        })
        return False
    return True


__all__ = ["select_rate_limiter", "consume_limiter"]

