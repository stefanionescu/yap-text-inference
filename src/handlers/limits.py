"""Simple sliding-window rate limiter helpers.

This module provides a time-based rate limiter using the sliding window
algorithm. It's used to prevent abuse by limiting:

- Messages per connection per time window
- Cancel requests per time window  
- Persona updates per time window

Sliding Window Algorithm:
    The limiter tracks timestamps of recent events in a deque. When a new
    event arrives:
    1. Remove timestamps older than (now - window_seconds)
    2. If remaining events >= limit, reject with retry_in time
    3. Otherwise, record the new timestamp and allow

This provides smoother rate limiting than fixed windows, as the limit
applies to any rolling window of the specified duration.

Example:
    limiter = SlidingWindowRateLimiter(limit=10, window_seconds=60)
    
    for message in messages:
        try:
            limiter.consume()
            process(message)
        except RateLimitError as e:
            await asyncio.sleep(e.retry_in)
"""

from __future__ import annotations

import time
import collections
from collections.abc import Callable

from src.errors import RateLimitError

# Type alias for injectable time functions (used in testing)
TimeFn = Callable[[], float]


class SlidingWindowRateLimiter:
    """Track events over a rolling window.
    
    This rate limiter uses a sliding window algorithm that provides smooth
    rate limiting without the "burst at window boundary" problem of fixed
    windows.
    
    The limiter can be disabled by setting limit=0 or window_seconds=0,
    in which case consume() always succeeds.
    
    Attributes:
        limit: Maximum events allowed per window.
        window_seconds: Duration of the sliding window.
    
    Example:
        # Allow 25 messages per 60 seconds
        limiter = SlidingWindowRateLimiter(limit=25, window_seconds=60)
        
        try:
            limiter.consume()  # Record event
        except RateLimitError as e:
            print(f"Rate limited, retry in {e.retry_in:.1f}s")
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: float,
        now_fn: TimeFn | None = None,
    ) -> None:
        """Initialize the rate limiter.
        
        Args:
            limit: Maximum events per window. Set to 0 to disable.
            window_seconds: Window duration in seconds. Set to 0 to disable.
            now_fn: Optional time function for testing. Defaults to time.monotonic.
        """
        self.limit = max(0, int(limit))
        self.window_seconds = max(0.0, float(window_seconds))
        self._now = now_fn or time.monotonic
        self._events: collections.deque[float] = collections.deque()
        self._enabled = self.limit > 0 and self.window_seconds > 0

    def consume(self) -> None:
        """Record an event or raise RateLimitError if the window is saturated.
        
        This method is thread-safe for single-threaded async code but should
        not be called concurrently from multiple threads.
        
        Raises:
            RateLimitError: If the rate limit has been exceeded.
        """
        if not self._enabled:
            return

        now = self._now()
        cutoff = now - self.window_seconds

        # Remove expired events from the front of the deque
        events = self._events
        while events and events[0] <= cutoff:
            events.popleft()

        # Check if we're at the limit
        if len(events) >= self.limit:
            # Calculate when the oldest event will expire
            retry_in = (events[0] + self.window_seconds) - now
            raise RateLimitError(
                retry_in=max(0.0, retry_in),
                limit=self.limit,
                window_seconds=self.window_seconds,
            )

        # Record this event
        events.append(now)


__all__ = ["RateLimitError", "SlidingWindowRateLimiter"]

