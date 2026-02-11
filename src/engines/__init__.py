"""Unified inference engine abstraction and runtime registry."""

from __future__ import annotations

from .sampling import create_sampling_params
from .base import BaseEngine, EngineOutput, EngineNotReadyError, EngineShutdownError
from .registry import (
    get_engine,
    shutdown_engine,
    reset_engine_caches,
    clear_engine_runtime,
    configure_engine_runtime,
    ensure_cache_reset_daemon,
    clear_caches_on_disconnect,
    engine_supports_cache_reset,
    cache_reset_reschedule_event,
    seconds_since_last_cache_reset,
)

__all__ = [
    # Base classes
    "BaseEngine",
    "EngineOutput",
    "EngineNotReadyError",
    "EngineShutdownError",
    # Runtime registry
    "configure_engine_runtime",
    "clear_engine_runtime",
    "get_engine",
    "shutdown_engine",
    "create_sampling_params",
    # Cache management (from registry)
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_caches_on_disconnect",
    "engine_supports_cache_reset",
    "ensure_cache_reset_daemon",
]
