"""vLLM engine implementation.

This package provides the vLLM-based inference backend. The heavy vLLM
dependency is only loaded when this package is actually imported - the
parent engines module defers imports to runtime via function-level imports.
"""

from __future__ import annotations

from .cache_daemon import ensure_cache_reset_daemon
from .engine import (
    VLLMEngine,
    cache_reset_reschedule_event,
    clear_caches_on_disconnect,
    get_engine,
    reset_engine_caches,
    seconds_since_last_cache_reset,
    shutdown_engine,
)
from .setup import configure_runtime_env

__all__ = [
    "VLLMEngine",
    "get_engine",
    "shutdown_engine",
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_caches_on_disconnect",
    "configure_runtime_env",
    "ensure_cache_reset_daemon",
]
