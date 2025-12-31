"""vLLM engine management for the chat engine.

This module wraps the vLLM AsyncLLMEngine with the BaseEngine interface
while preserving all existing functionality including cache management.

Architecture:
    - VLLMEngine: BaseEngine implementation wrapping AsyncLLMEngine
    - Singleton pattern with async-safe initialization via _ENGINE_LOCK
    - Cache reset with rate limiting via _CACHE_RESET_LOCK and interval check

Key Features:
    1. Streaming generation with EngineOutput conversion
    2. Request abortion for cancellation support
    3. Prefix/multimodal cache reset for memory management
    4. AWQ offline mode handling for local quantized models

Environment Variables (set as defaults):
    VLLM_USE_V1=1: Use vLLM V1 engine architecture
    VLLM_WORKER_MULTIPROC_METHOD=spawn: Use spawn instead of fork

Cache Reset Strategy:
    - Rate-limited by CACHE_RESET_INTERVAL_SECONDS
    - Force reset available for critical situations
    - Event signaling for cache reset daemon coordination
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import time
from typing import Any
from collections.abc import AsyncGenerator

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm.engine.async_llm_engine import AsyncLLMEngine

from src.config import (
    CACHE_RESET_INTERVAL_SECONDS,
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    DEPLOY_CHAT,
)
from ..base import BaseEngine, EngineOutput
from .args import make_engine_args
from .fallback import create_engine_with_fallback

logger = logging.getLogger(__name__)

# Module-level singleton state
_ENGINE: "VLLMEngine | None" = None  # Singleton engine instance
_ENGINE_LOCK = asyncio.Lock()  # Guards engine initialization
_CACHE_RESET_LOCK = asyncio.Lock()  # Guards cache reset operations
_CACHE_RESET_EVENT = asyncio.Event()  # Signals cache reset to daemon
_LAST_CACHE_RESET = time.monotonic()  # For rate limiting resets


class VLLMEngine(BaseEngine):
    """vLLM-based inference engine with cache management.
    
    This class wraps AsyncLLMEngine to provide:
    - BaseEngine interface compliance
    - Unified EngineOutput format
    - Cache reset support for memory management
    
    Attributes:
        _engine: The underlying vLLM AsyncLLMEngine instance.
    """
    
    def __init__(self, llm_engine: AsyncLLMEngine):
        """Initialize with a vLLM AsyncLLMEngine.
        
        Args:
            llm_engine: Pre-configured AsyncLLMEngine instance.
        """
        self._engine = llm_engine
    
    @property
    def raw_engine(self) -> AsyncLLMEngine:
        """Access the underlying vLLM engine."""
        return self._engine
    
    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation using vLLM's generate API.
        
        Args:
            prompt: The formatted prompt to generate from.
            sampling_params: vLLM SamplingParams instance.
            request_id: Unique identifier for tracking/abortion.
            
        Yields:
            EngineOutput with cumulative text and completion status.
        """
        async for output in self._engine.generate(
            prompt=prompt,
            sampling_params=sampling_params,
            request_id=request_id,
        ):
            yield EngineOutput.from_vllm(output)
    
    async def abort(self, request_id: str) -> None:
        """Abort a vLLM generation request."""
        with contextlib.suppress(Exception):
            await self._engine.abort(request_id)
    
    async def shutdown(self) -> None:
        """Shutdown the vLLM engine."""
        try:
            await self._engine.shutdown()
            logger.info("vLLM: engine shutdown complete")
        except Exception:
            logger.warning("vLLM: engine shutdown failed", exc_info=True)
    
    @property
    def supports_cache_reset(self) -> bool:
        """vLLM supports prefix/mm cache reset."""
        return True
    
    async def reset_caches(self, reason: str) -> bool:
        """Reset vLLM prefix and multimodal caches."""
        logger.info("resetting vLLM cache (reason=%s)", reason)
        try:
            await _reset_vllm_caches(self._engine)
            return True
        except Exception:
            logger.warning("cache reset failed", exc_info=True)
            return False


_VLLM_CACHE_RESET_METHODS = ("reset_mm_cache", "reset_prefix_cache")


async def _reset_vllm_caches(engine: AsyncLLMEngine) -> None:
    """Best-effort reset of vLLM prefix and multimodal caches."""
    for method_name in _VLLM_CACHE_RESET_METHODS:
        method = getattr(engine, method_name, None)
        if method is None:
            continue
        try:
            result = method()
            if asyncio.iscoroutine(result):
                await result
        except Exception:
            pass  # Best effort only


# ============================================================================
# Global engine management (singleton pattern)
# ============================================================================
async def _ensure_engine() -> VLLMEngine:
    """Ensure the vLLM engine is initialized."""
    if not DEPLOY_CHAT:
        raise RuntimeError("Chat engine requested but DEPLOY_CHAT=0")
    global _ENGINE
    if _ENGINE is not None:
        return _ENGINE

    async with _ENGINE_LOCK:
        if _ENGINE is not None:
            return _ENGINE
        if not CHAT_MODEL:
            raise RuntimeError("CHAT_MODEL is not configured; cannot start chat engine")
        logger.info("vLLM: building chat engine (model=%s)", CHAT_MODEL)
        engine_args = make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN)
        raw_engine = create_engine_with_fallback(engine_args)
        _ENGINE = VLLMEngine(raw_engine)
        logger.info("vLLM: chat engine ready")
        return _ENGINE


async def get_engine() -> VLLMEngine:
    """Return the singleton chat engine instance."""
    return await _ensure_engine()


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    """Reset prefix/MM caches if interval elapsed (or force)."""
    global _LAST_CACHE_RESET

    engine = _ENGINE
    if engine is None:
        return False

    interval = CACHE_RESET_INTERVAL_SECONDS
    now = time.monotonic()
    if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
        return False

    async with _CACHE_RESET_LOCK:
        now = time.monotonic()
        if not force and interval > 0 and (now - _LAST_CACHE_RESET) < interval:
            return False

        success = await engine.reset_caches(reason)
        if success:
            _LAST_CACHE_RESET = time.monotonic()

            _CACHE_RESET_EVENT.set()
        return success


def seconds_since_last_cache_reset() -> float:
    """Return seconds since the last cache reset."""
    return max(0.0, time.monotonic() - _LAST_CACHE_RESET)


def cache_reset_reschedule_event() -> asyncio.Event:
    """Return the event used to signal cache reset rescheduling."""
    return _CACHE_RESET_EVENT


async def shutdown_engine() -> None:
    """Shut down the chat engine if it has been initialized."""
    global _ENGINE
    engine = _ENGINE
    if engine is None:
        return

    async with _ENGINE_LOCK:
        engine = _ENGINE
        if engine is None:
            return
        await engine.shutdown()
        _ENGINE = None


async def clear_all_engine_caches_on_disconnect() -> None:
    """Force cache reset when all clients disconnect."""
    await reset_engine_caches("all_clients_disconnected", force=True)
