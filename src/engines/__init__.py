"""Unified inference engine abstraction.

This module provides a factory-based abstraction layer that supports both
vLLM and TensorRT-LLM inference backends.

All engine lifecycle functions are delegated to the central registry
(src/engines/registry.py), which owns the singleton instances.

1. Engine Access:
   - get_engine(): Returns configured engine (vLLM or TRT-LLM)
   - Lazy initialization on first call
   - Thread-safe singleton pattern

2. Sampling Parameters:
   - create_sampling_params(): Engine-agnostic param creation
   - Handles parameter name/format differences between engines

3. Lifecycle Management:
   - shutdown_engine(): Clean shutdown of all engines
   - Used during graceful server termination

4. Cache Management (vLLM only):
   - reset_engine_caches(): Clear prefix/multimodal caches
   - cache_reset_reschedule_event(): Event for cache reset daemon
   - clear_caches_on_disconnect(): Cleanup on last client
   - TRT-LLM uses block reuse instead of explicit cache resets

Engine Selection:
    Controlled by INFERENCE_ENGINE environment variable:
    - 'vllm': Use vLLM AsyncLLMEngine (default)
    - 'trt': Use TensorRT-LLM

Usage:
    from src.engines import get_engine, create_sampling_params

    engine = await get_engine()
    params = create_sampling_params(temperature=0.7, max_tokens=256)
    async for output in engine.generate_stream(prompt, params, request_id):
        print(output.text)
"""

from __future__ import annotations

from .sampling import create_sampling_params
from .warmup import warm_classifier, warm_chat_engine
from .base import BaseEngine, EngineOutput, EngineNotReadyError, EngineShutdownError

# Re-export registry functions as the public API
from .registry import (
    get_engine,
    shutdown_engine,
    reset_engine_caches,
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
    # Factory functions (from registry)
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
    # Warmup utilities
    "warm_chat_engine",
    "warm_classifier",
]
