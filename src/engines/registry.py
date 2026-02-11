"""Central registry for configured engine runtime dependencies.

Engine instances are built eagerly during startup and registered here for
shared access. No lazy singleton initialization is performed in this module.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from .base import BaseEngine
    from .vllm.cache import CacheResetManager


class _RuntimeState(TypedDict):
    engine: BaseEngine | None
    cache_reset_manager: CacheResetManager | None


_STATE: _RuntimeState = {
    "engine": None,
    "cache_reset_manager": None,
}
_NOOP_CACHE_EVENT = asyncio.Event()


def configure_engine_runtime(
    engine: BaseEngine | None,
    cache_reset_manager: CacheResetManager | None = None,
) -> None:
    """Register runtime engine dependencies."""
    _STATE["engine"] = engine
    _STATE["cache_reset_manager"] = cache_reset_manager


def clear_engine_runtime() -> None:
    """Clear configured runtime engine dependencies."""
    configure_engine_runtime(None, None)


async def get_engine() -> BaseEngine:
    """Return configured runtime chat engine."""
    engine = _STATE["engine"]
    if engine is None:
        raise RuntimeError("Chat engine has not been configured in runtime bootstrap")
    return engine


async def shutdown_engine() -> None:
    """Shutdown configured engine and clear runtime references."""
    engine = _STATE["engine"]
    clear_engine_runtime()
    if engine is not None:
        await engine.shutdown()


def engine_supports_cache_reset() -> bool:
    """Check whether configured runtime engine supports cache reset."""
    engine = _STATE["engine"]
    cache_reset_manager = _STATE["cache_reset_manager"]
    return engine is not None and engine.supports_cache_reset and cache_reset_manager is not None


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    """Reset configured engine caches (vLLM only)."""
    if not engine_supports_cache_reset():
        return False
    engine = _STATE["engine"]
    cache_reset_manager = _STATE["cache_reset_manager"]
    if engine is None or cache_reset_manager is None:
        return False
    return await cache_reset_manager.try_reset(engine, reason, force=force)


def cache_reset_reschedule_event() -> asyncio.Event:
    """Get cache reset reschedule event if available."""
    cache_reset_manager = _STATE["cache_reset_manager"]
    if cache_reset_manager is None:
        return _NOOP_CACHE_EVENT
    return cache_reset_manager.reschedule_event


def seconds_since_last_cache_reset() -> float:
    """Get elapsed seconds since previous cache reset."""
    cache_reset_manager = _STATE["cache_reset_manager"]
    if cache_reset_manager is None:
        return 0.0
    return cache_reset_manager.seconds_since_last_reset()


async def clear_caches_on_disconnect() -> None:
    """Clear caches when no active clients remain (vLLM only)."""
    if engine_supports_cache_reset():
        await reset_engine_caches("all_clients_disconnected", force=True)


def ensure_cache_reset_daemon() -> None:
    """Ensure cache reset daemon is running when available."""
    cache_reset_manager = _STATE["cache_reset_manager"]
    if not engine_supports_cache_reset() or cache_reset_manager is None:
        return
    cache_reset_manager.ensure_daemon_running(
        lambda reason, force: reset_engine_caches(reason, force=force),
    )


__all__ = [
    "configure_engine_runtime",
    "clear_engine_runtime",
    "get_engine",
    "shutdown_engine",
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_caches_on_disconnect",
    "engine_supports_cache_reset",
    "ensure_cache_reset_daemon",
]
