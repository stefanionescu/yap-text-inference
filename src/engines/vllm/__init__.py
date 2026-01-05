"""vLLM engine implementation.

This package provides the vLLM-based inference backend. The heavy vLLM
dependency is only loaded when this package is actually imported - the
parent engines module defers imports to runtime via function-level imports.

Note: Runtime environment configuration (VLLM_USE_V1, etc.) is applied
lazily when get_engine() is first called, not at import time.
"""

from __future__ import annotations

from .cache import (
    cache_reset_reschedule_event,
    ensure_cache_reset_daemon,
    seconds_since_last_cache_reset,
)
from .engine import VLLMEngine
from .factory import (
    clear_caches_on_disconnect,
    get_engine,
    reset_engine_caches,
    shutdown_engine,
)
from .setup import configure_runtime_env

__all__ = [
    "VLLMEngine",
    "cache_reset_reschedule_event",
    "clear_caches_on_disconnect",
    "configure_runtime_env",
    "ensure_cache_reset_daemon",
    "get_engine",
    "reset_engine_caches",
    "seconds_since_last_cache_reset",
    "shutdown_engine",
]
