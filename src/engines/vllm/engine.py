"""vLLM engine wrapper implementing BaseEngine interface.

This module provides the VLLMEngine class that wraps vLLM's AsyncLLMEngine
with the BaseEngine interface while preserving cache management functionality.

Key Features:
    1. Streaming generation with EngineOutput conversion
    2. Request abortion for cancellation support
    3. Prefix/multimodal cache reset for memory management
"""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any
from collections.abc import AsyncGenerator

from vllm.engine.async_llm_engine import AsyncLLMEngine

from ..base import BaseEngine, EngineOutput

logger = logging.getLogger(__name__)


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


# ============================================================================
# Cache reset helpers
# ============================================================================
_CACHE_RESET_METHOD_NAMES = ("reset_mm_cache", "reset_prefix_cache")


async def _reset_vllm_caches(engine: AsyncLLMEngine) -> None:
    """Best-effort reset of vLLM prefix and multimodal caches."""
    for method_name in _CACHE_RESET_METHOD_NAMES:
        method = getattr(engine, method_name, None)
        if method is None:
            continue
        with contextlib.suppress(Exception):
            result = method()
            if asyncio.iscoroutine(result):
                await result


__all__ = ["VLLMEngine"]
