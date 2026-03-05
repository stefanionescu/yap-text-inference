"""Rate limiting utilities for WebSocket message handling.

This module provides rate limit selection and consumption for different
message types:

- Regular messages: Limited to prevent spam
- Cancel messages: Separate bucket to prevent cancel bursts starving messages
- Control messages (ping/pong/end): Exempt from rate limiting
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from .helpers import safe_send_flat
from ...telemetry.instruments import get_metrics
from ..limits import RateLimitError, SlidingWindowRateLimiter
from ...config.websocket import WS_ERROR_RATE_LIMITED, WS_STATUS_RATE_LIMITED

if TYPE_CHECKING:
    from fastapi import WebSocket


def select_rate_limiter(
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> tuple[SlidingWindowRateLimiter | None, str]:
    """Pick which limiter applies to the message type (if any)."""
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
    """Attempt to consume a limiter token, sending an error on failure."""
    try:
        limiter.consume()
    except RateLimitError:
        get_metrics().rate_limit_violations_total.add(1)
        await safe_send_flat(
            ws,
            "error",
            status=WS_STATUS_RATE_LIMITED,
            code=WS_ERROR_RATE_LIMITED,
            message="Rate limit exceeded. Try again shortly.",
        )
        return False
    return True


__all__ = ["select_rate_limiter", "consume_limiter"]
