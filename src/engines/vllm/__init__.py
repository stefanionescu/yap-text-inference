"""vLLM engine implementation.

This package exposes the vLLM-based inference backend while keeping the
heavy `vllm` dependency lazily imported. Quantization utilities that only
need the AWQ helpers can safely import ``src.engines.vllm`` without pulling
the runtime wheel into their virtual environment.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from .engine import (
        VLLMEngine,
        cache_reset_reschedule_event,
        clear_all_engine_caches_on_disconnect,
        get_engine,
        reset_engine_caches,
        seconds_since_last_cache_reset,
        shutdown_engines,
    )


def __getattr__(name: str):
    """Lazily expose engine symbols to avoid importing vLLM eagerly."""

    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(".engine", __name__)
    value = getattr(module, name)
    globals()[name] = value  # Cache attribute for future lookups
    return value


def __dir__() -> list[str]:
    return sorted(set(__all__ + list(globals().keys())))


__all__ = [
    "VLLMEngine",
    "get_engine",
    "shutdown_engines",
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_all_engine_caches_on_disconnect",
]