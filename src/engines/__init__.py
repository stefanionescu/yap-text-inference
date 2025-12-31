"""Unified inference engine abstraction.

This module provides a factory-based abstraction layer that supports both
vLLM and TensorRT-LLM inference backends. The module handles:

1. Engine Factory:
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

import asyncio
from typing import TYPE_CHECKING

from src.config import INFERENCE_ENGINE

from .base import BaseEngine, EngineOutput, EngineNotReadyError, EngineShutdownError
from .sampling import create_sampling_params

if TYPE_CHECKING:
    pass


async def get_engine() -> BaseEngine:
    """Get the configured inference engine.
    
    Returns the appropriate engine based on INFERENCE_ENGINE:
    - 'vllm': Returns VLLMEngine
    - 'trt': Returns TRTEngine
    
    The engine is lazily initialized on first call.
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm import get_engine as get_vllm_engine
        return await get_vllm_engine()
    else:
        from .trt import get_engine as get_trt_engine
        return await get_trt_engine()


async def shutdown_engine() -> None:
    """Shutdown all initialized engines."""
    if INFERENCE_ENGINE == "vllm":
        from .vllm import shutdown_engine as shutdown_vllm
        await shutdown_vllm()
    else:
        from .trt import shutdown_engine as shutdown_trt
        await shutdown_trt()


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    """Reset engine caches if supported.
    
    For vLLM: Resets prefix and multimodal caches.
    For TRT-LLM: No-op (block reuse handles memory management).
    
    Args:
        reason: Human-readable reason for the reset.
        force: Force reset even if interval hasn't elapsed.
        
    Returns:
        True if caches were reset, False otherwise.
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm import reset_engine_caches as reset_vllm_caches
        return await reset_vllm_caches(reason, force=force)
    else:
        # TRT-LLM doesn't need cache resets
        return False


def cache_reset_reschedule_event() -> asyncio.Event:
    """Get the cache reset reschedule event (vLLM only).
    
    For TRT-LLM, returns a dummy event that's never set.
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm import cache_reset_reschedule_event as vllm_event
        return vllm_event()
    else:
        # Return a dummy event for TRT that's never used
        return asyncio.Event()


def seconds_since_last_cache_reset() -> float:
    """Get seconds since last cache reset (vLLM only).
    
    For TRT-LLM, returns 0.0 (cache reset not applicable).
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm import seconds_since_last_cache_reset as vllm_seconds
        return vllm_seconds()
    else:
        return 0.0


async def clear_caches_on_disconnect() -> None:
    """Clear caches when all clients disconnect (vLLM only)."""
    if INFERENCE_ENGINE == "vllm":
        from .vllm import clear_caches_on_disconnect as vllm_clear
        await vllm_clear()
    # TRT-LLM: no-op


def engine_supports_cache_reset() -> bool:
    """Check if the current engine supports cache reset operations."""
    return INFERENCE_ENGINE == "vllm"


__all__ = [
    # Base classes
    "BaseEngine",
    "EngineOutput",
    "EngineNotReadyError",
    "EngineShutdownError",
    # Factory functions
    "get_engine",
    "shutdown_engine",
    "create_sampling_params",
    # Cache management
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_caches_on_disconnect",
    "engine_supports_cache_reset",
]

