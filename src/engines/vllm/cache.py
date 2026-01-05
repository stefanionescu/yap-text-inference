"""vLLM cache reset state, management, and background daemon.

This module manages cache reset state and provides a background daemon for
periodic memory management. Cache resets are rate-limited to avoid overhead.

Cache Reset Strategy:
    - Rate-limited by CACHE_RESET_INTERVAL_SECONDS
    - Force reset available for critical situations
    - Event signaling for daemon coordination

Note:
    TRT-LLM handles memory differently via block reuse and does not need
    cache resets - this is vLLM-specific.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Callable, Awaitable

from src.config import CACHE_RESET_INTERVAL_SECONDS

logger = logging.getLogger(__name__)

# Cache reset state
_CACHE_RESET_LOCK = asyncio.Lock()  # Guards cache reset operations
_CACHE_RESET_EVENT = asyncio.Event()  # Signals cache reset to daemon
_LAST_CACHE_RESET = time.monotonic()  # For rate limiting resets

# Daemon state
_cache_reset_task: asyncio.Task | None = None

# Type alias for the reset function signature
ResetCachesFn = Callable[[str, bool], Awaitable[bool]]


def seconds_since_last_cache_reset() -> float:
    """Return seconds since the last cache reset."""
    return max(0.0, time.monotonic() - _LAST_CACHE_RESET)


def cache_reset_reschedule_event() -> asyncio.Event:
    """Return the event used to signal cache reset rescheduling."""
    return _CACHE_RESET_EVENT


async def try_reset_caches(
    engine: object,
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
    global _LAST_CACHE_RESET

    interval = CACHE_RESET_INTERVAL_SECONDS
    now = time.monotonic()
    if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
        return False

    async with _CACHE_RESET_LOCK:
        now = time.monotonic()
        if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
            return False

        reset_method = getattr(engine, "reset_caches", None)
        if reset_method is None:
            return False

        success = await reset_method(reason)
        if success:
            _LAST_CACHE_RESET = time.monotonic()
            _CACHE_RESET_EVENT.set()
        return success


# ============================================================================
# Background Daemon
# ============================================================================

async def _cache_reset_daemon_loop(reset_caches_fn: ResetCachesFn) -> None:
    """Background task to periodically reset vLLM caches.

    Runs on a configurable interval (default 600s) to reset prefix cache
    and multimodal cache. Uses event-based scheduling that can be interrupted
    when a long session ends.
    
    Args:
        reset_caches_fn: Async function(reason, force) -> bool for cache reset.
    """
    interval = CACHE_RESET_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("cache reset daemon disabled")
        return

    event = cache_reset_reschedule_event()
    logger.info("cache reset daemon started interval=%ss", interval)

    while True:
        if event.is_set():
            event.clear()
            continue

        wait = max(0.0, interval - seconds_since_last_cache_reset())
        if wait <= 0:
            await reset_caches_fn("timer", True)
            continue

        try:
            await asyncio.wait_for(event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            await reset_caches_fn("timer", True)
        else:
            if event.is_set():
                event.clear()


def ensure_cache_reset_daemon(reset_caches_fn: ResetCachesFn) -> None:
    """Start the cache reset daemon if configuration enables it.

    Safe to call multiple times - will not start duplicate daemons.
    
    Args:
        reset_caches_fn: Async function(reason, force) -> bool for cache reset.
                         Typically factory.reset_engine_caches.
    """
    global _cache_reset_task
    if _cache_reset_task and not _cache_reset_task.done():
        return
    if CACHE_RESET_INTERVAL_SECONDS <= 0:
        return
    _cache_reset_task = asyncio.create_task(_cache_reset_daemon_loop(reset_caches_fn))


__all__ = [
    "cache_reset_reschedule_event",
    "ensure_cache_reset_daemon",
    "seconds_since_last_cache_reset",
    "try_reset_caches",
]
