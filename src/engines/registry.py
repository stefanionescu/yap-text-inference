"""Central registry for inference engine singleton instances.

This module owns all engine singleton instances, providing a single location
for lifecycle management. Entry-point code (server.py) interacts with this
registry; other modules receive engine instances as parameters.

The registry uses lazy initialization - singletons are created on first access,
not at import time.

Usage:
    from src.engines.registry import get_engine, shutdown_engine
    
    engine = await get_engine()
    await shutdown_engine()
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from src.config import INFERENCE_ENGINE

if TYPE_CHECKING:
    from .base import BaseEngine
    from .trt.factory import TRTEngineSingleton
    from .vllm.factory import VLLMEngineSingleton

# Singleton instances - created lazily on first access
_trt_singleton: TRTEngineSingleton | None = None
_vllm_singleton: VLLMEngineSingleton | None = None


def _get_trt_singleton() -> TRTEngineSingleton:
    """Get or create the TRT engine singleton manager."""
    global _trt_singleton
    if _trt_singleton is None:
        from .trt.factory import TRTEngineSingleton
        _trt_singleton = TRTEngineSingleton()
    return _trt_singleton


def _get_vllm_singleton() -> VLLMEngineSingleton:
    """Get or create the vLLM engine singleton manager."""
    global _vllm_singleton
    if _vllm_singleton is None:
        from .vllm.factory import VLLMEngineSingleton
        _vllm_singleton = VLLMEngineSingleton()
    return _vllm_singleton


async def get_engine() -> BaseEngine:
    """Get the configured inference engine instance.
    
    Returns the appropriate engine based on INFERENCE_ENGINE config:
    - 'vllm': Returns VLLMEngine
    - 'trt': Returns TRTEngine
    
    The engine is lazily initialized on first call.
    """
    if INFERENCE_ENGINE == "vllm":
        return await _get_vllm_singleton().get()
    return await _get_trt_singleton().get()


async def shutdown_engine() -> None:
    """Shutdown all initialized engines."""
    if INFERENCE_ENGINE == "vllm":
        singleton = _get_vllm_singleton()
        if singleton.is_initialized:
            await singleton.shutdown()
    else:
        singleton = _get_trt_singleton()
        if singleton.is_initialized:
            await singleton.shutdown()


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
    if INFERENCE_ENGINE != "vllm":
        return False
    
    singleton = _get_vllm_singleton()
    if not singleton.is_initialized:
        return False
    
    from .vllm.cache import CacheResetManager
    engine = await singleton.get()
    return await CacheResetManager.get_instance().try_reset(engine, reason, force=force)


def cache_reset_reschedule_event() -> asyncio.Event:
    """Get the cache reset reschedule event (vLLM only).
    
    For TRT-LLM, returns a dummy event that's never set.
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm.cache import CacheResetManager
        return CacheResetManager.get_instance().reschedule_event
    return asyncio.Event()


def seconds_since_last_cache_reset() -> float:
    """Get seconds since last cache reset (vLLM only).
    
    For TRT-LLM, returns 0.0 (cache reset not applicable).
    """
    if INFERENCE_ENGINE == "vllm":
        from .vllm.cache import CacheResetManager
        return CacheResetManager.get_instance().seconds_since_last_reset()
    return 0.0


async def clear_caches_on_disconnect() -> None:
    """Clear caches when all clients disconnect (vLLM only)."""
    if INFERENCE_ENGINE == "vllm":
        await reset_engine_caches("all_clients_disconnected", force=True)


def engine_supports_cache_reset() -> bool:
    """Check if the current engine supports cache reset operations."""
    return INFERENCE_ENGINE == "vllm"


def ensure_cache_reset_daemon() -> None:
    """Start the cache reset daemon if configuration enables it.
    
    Safe to call multiple times - will not start duplicate daemons.
    Only applicable for vLLM engine.
    """
    if INFERENCE_ENGINE != "vllm":
        return
    
    from .vllm.cache import CacheResetManager
    CacheResetManager.get_instance().ensure_daemon_running(reset_engine_caches)


__all__ = [
    "get_engine",
    "shutdown_engine",
    "reset_engine_caches",
    "cache_reset_reschedule_event",
    "seconds_since_last_cache_reset",
    "clear_caches_on_disconnect",
    "engine_supports_cache_reset",
    "ensure_cache_reset_daemon",
]

