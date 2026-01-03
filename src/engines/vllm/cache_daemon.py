"""vLLM cache reset daemon for periodic memory management.

This module provides a background daemon that periodically clears vLLM's
prefix cache and multimodal cache to prevent memory fragmentation over time.
This is especially important for:

- Long-running deployments
- High-volume traffic with diverse prompts
- Models with prefix caching enabled

Note:
    TRT-LLM handles memory differently via block reuse and does not need
    this daemon - it is vLLM-specific.
"""

from __future__ import annotations

import asyncio
import logging

from src.config import CACHE_RESET_INTERVAL_SECONDS
from .engine import (
    cache_reset_reschedule_event,
    reset_engine_caches,
    seconds_since_last_cache_reset,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Daemon State
# ============================================================================

# Global task reference for the cache reset daemon
# This allows the daemon to be stopped on shutdown
_cache_reset_task: asyncio.Task | None = None


# ============================================================================
# Internal Daemon Loop
# ============================================================================

async def _cache_reset_daemon_loop() -> None:
    """Background task to periodically reset vLLM caches.

    This daemon runs on a configurable interval (default 600s) and:
    1. Resets the prefix cache (frees computed attention states)
    2. Resets the multimodal cache (frees image/audio embeddings)

    The daemon uses an event-based scheduling system that can be interrupted
    when a long session ends, triggering an immediate reset instead of
    waiting for the timer.
    """
    interval = CACHE_RESET_INTERVAL_SECONDS
    if interval <= 0:
        logger.info("cache reset daemon disabled")
        return

    # Event used to interrupt the wait (e.g., after a long session ends)
    event = cache_reset_reschedule_event()
    logger.info("cache reset daemon started interval=%ss", interval)

    while True:
        # Check if we were signaled to reset immediately
        if event.is_set():
            event.clear()
            continue

        # Calculate remaining wait time
        wait = max(0.0, interval - seconds_since_last_cache_reset())
        if wait <= 0:
            # Timer expired - reset caches now
            await reset_engine_caches("timer", force=True)
            continue

        try:
            # Wait for either the timer or an interrupt signal
            await asyncio.wait_for(event.wait(), timeout=wait)
        except asyncio.TimeoutError:
            # Timer expired - reset caches
            await reset_engine_caches("timer", force=True)
        else:
            # Event was set - someone requested a reschedule
            if event.is_set():
                event.clear()


# ============================================================================
# Public API
# ============================================================================

def ensure_cache_reset_daemon() -> None:
    """Start the cache reset daemon if configuration enables it.

    The cache reset daemon periodically clears vLLM's prefix cache and
    multimodal cache to prevent memory fragmentation over time.

    Safe to call multiple times - will not start duplicate daemons.
    """
    global _cache_reset_task
    # Don't start if already running
    if _cache_reset_task and not _cache_reset_task.done():
        return
    # Don't start if cache reset is disabled
    if CACHE_RESET_INTERVAL_SECONDS <= 0:
        return
    _cache_reset_task = asyncio.create_task(_cache_reset_daemon_loop())


__all__ = ["ensure_cache_reset_daemon"]

