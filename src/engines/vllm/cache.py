"""vLLM cache reset manager and background daemon.

This module provides the CacheResetManager class that encapsulates all cache
reset state and provides a background daemon for periodic memory management.

Cache Reset Strategy:
    - Rate-limited by CACHE_RESET_INTERVAL_SECONDS
    - Force reset available for critical situations
    - Event signaling for daemon coordination

Note:
    TRT-LLM handles memory differently via block reuse and does not need
    cache resets - this is vLLM-specific.
"""

from __future__ import annotations

import time
import asyncio
import logging
from typing import TYPE_CHECKING
from collections.abc import Callable, Awaitable
from src.config import CACHE_RESET_INTERVAL_SECONDS

if TYPE_CHECKING:
    from src.engines.base import BaseEngine

logger = logging.getLogger(__name__)

# Type alias for the reset function signature
ResetCachesFn = Callable[[str, bool], Awaitable[bool]]


class CacheResetManager:
    """Encapsulates cache reset state and daemon lifecycle.

    This class manages:
    - Rate-limiting of cache resets
    - Event signaling for daemon coordination
    - Background daemon for periodic resets

    This manager is instantiated during runtime bootstrap and passed into
    request-handling code through the runtime dependency container.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()
        self._last_reset = time.monotonic()
        self._daemon_task: asyncio.Task[None] | None = None

    @property
    def reschedule_event(self) -> asyncio.Event:
        """Return the event used to signal cache reset rescheduling."""
        return self._event

    def seconds_since_last_reset(self) -> float:
        """Return seconds since the last cache reset."""
        return max(0.0, time.monotonic() - self._last_reset)

    async def try_reset(
        self,
        engine: BaseEngine,
        reason: str,
        *,
        force: bool = False,
    ) -> bool:
        """Attempt to reset caches if interval has elapsed or force is True.

        Handles rate-limiting and locking. Actual reset delegated to engine.

        Args:
            engine: Engine instance with reset_caches method.
            reason: Human-readable reason for the reset.
            force: Force reset even if interval hasn't elapsed.

        Returns:
            True if caches were reset, False otherwise.
        """
        interval = CACHE_RESET_INTERVAL_SECONDS
        now = time.monotonic()
        if not force and interval > 0 and (now - self._last_reset) < interval:
            return False

        async with self._lock:
            now = time.monotonic()
            if not force and interval > 0 and (now - self._last_reset) < interval:
                return False

            reset_method = getattr(engine, "reset_caches", None)
            if reset_method is None:
                return False

            success = await reset_method(reason)
            if success:
                self._last_reset = time.monotonic()
                self._event.set()
            return success

    def ensure_daemon_running(self, reset_caches_fn: ResetCachesFn) -> None:
        """Start the cache reset daemon if configuration enables it.

        Safe to call multiple times - will not start duplicate daemons.

        Args:
            reset_caches_fn: Async function(reason, force) -> bool for cache reset.
                            Typically registry.reset_engine_caches.
        """
        if self._daemon_task and not self._daemon_task.done():
            return
        if CACHE_RESET_INTERVAL_SECONDS <= 0:
            return
        self._daemon_task = asyncio.create_task(self._daemon_loop(reset_caches_fn))

    async def _daemon_loop(self, reset_caches_fn: ResetCachesFn) -> None:
        """Background task to periodically reset vLLM caches.

        Runs on a configurable interval (CACHE_RESET_INTERVAL_SECONDS) to reset
        prefix cache and multimodal cache. Uses event-based scheduling that can
        be interrupted when a long session ends.

        Args:
            reset_caches_fn: Async function(reason, force) -> bool for cache reset.
        """
        interval = CACHE_RESET_INTERVAL_SECONDS
        if interval <= 0:
            logger.info("cache reset daemon disabled")
            return

        logger.info("cache reset daemon started interval=%ss", interval)

        while True:
            if self._event.is_set():
                self._event.clear()
                continue

            wait = max(0.0, interval - self.seconds_since_last_reset())
            if wait <= 0:
                await reset_caches_fn("timer", True)
                continue

            try:
                await asyncio.wait_for(self._event.wait(), timeout=wait)
            except TimeoutError:
                await reset_caches_fn("timer", True)
            else:
                if self._event.is_set():
                    self._event.clear()


__all__ = ["CacheResetManager", "ResetCachesFn"]
