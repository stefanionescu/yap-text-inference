"""Client-side pacing helpers mirroring server rolling windows."""

from __future__ import annotations

import time
import asyncio
import collections
from collections import deque


class SlidingWindowPacer:
    """Asynchronous pacer that enforces a rolling window cap."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = max(0, int(limit))
        self.window_seconds = max(0.0, float(window_seconds))
        self._events: deque[float] = collections.deque()

    @property
    def enabled(self) -> bool:
        return self.limit > 0 and self.window_seconds > 0

    async def wait_turn(self) -> None:
        """Sleep just enough so the next event fits inside the window."""
        if not self.enabled:
            return

        while True:
            now = time.monotonic()
            self._trim(now)
            if len(self._events) < self.limit:
                self._events.append(now)
                return

            # Window is saturated; wait for the oldest event to expire.
            earliest = self._events[0]
            sleep_for = (earliest + self.window_seconds) - now
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            else:
                # Should be expired already; drop and loop.
                self._events.popleft()

    def _trim(self, now: float) -> None:
        cutoff = now - self.window_seconds
        events = self._events
        while events and events[0] <= cutoff:
            events.popleft()


__all__ = ["SlidingWindowPacer"]

