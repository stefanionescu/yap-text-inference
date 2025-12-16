"""vLLM engine implementation.

This package provides the vLLM-based inference backend, wrapping the
vLLM AsyncLLMEngine with the BaseEngine interface. It includes:

VLLMEngine:
    The main engine class implementing BaseEngine. Provides streaming
    generation, request abortion, and cache management.

Factory Functions:
    get_engine() / get_chat_engine(): Return singleton engine instance
    shutdown_engines(): Clean shutdown of all engines

Cache Management:
    reset_engine_caches(): Clear prefix and multimodal caches
    cache_reset_reschedule_event(): Event for cache reset daemon
    seconds_since_last_cache_reset(): Time since last reset
    clear_all_engine_caches_on_disconnect(): Cleanup on last client

The engine uses vLLM V1 by default (VLLM_USE_V1=1) and spawned workers
(VLLM_WORKER_MULTIPROC_METHOD=spawn) for stability.
"""

from .engine import (
    VLLMEngine,
    get_engine,
    get_chat_engine,
    shutdown_engines,
    reset_engine_caches,
    cache_reset_reschedule_event,
    seconds_since_last_cache_reset,
    clear_all_engine_caches_on_disconnect,
)

__all__ = [
    "VLLMEngine",
    "get_engine",
    "get_chat_engine",
    "shutdown_engines",
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_all_engine_caches_on_disconnect",
]

