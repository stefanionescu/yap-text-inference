"""TensorRT-LLM engine management for the chat engine.

This module provides the TRT-LLM engine wrapper implementing the BaseEngine interface.
Unlike vLLM, TRT-LLM uses pre-built engines and does not need periodic cache resets
due to its built-in KV cache block reuse mechanism.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
from typing import Any
from collections.abc import AsyncGenerator

from src.config import (
    CHAT_MODEL,
    DEPLOY_CHAT,
    TRT_ENGINE_DIR,
    TRT_KV_FREE_GPU_FRAC,
    TRT_KV_ENABLE_BLOCK_REUSE,
)
from ..base import BaseEngine, EngineOutput, EngineNotReadyError

logger = logging.getLogger(__name__)

_ENGINE: "TRTEngine | None" = None
_ENGINE_LOCK = asyncio.Lock()


class TRTEngine(BaseEngine):
    """TensorRT-LLM based inference engine.
    
    TRT-LLM engines are pre-built and loaded from a directory containing
    the compiled TensorRT engine files (e.g., rank0.engine).
    
    Key differences from vLLM:
    - No periodic cache reset needed (block reuse is built-in)
    - Engine is pre-compiled, not JIT compiled
    - Uses different SamplingParams class
    """
    
    def __init__(self, llm: Any, tokenizer_id: str):
        """Initialize TRT engine wrapper.
        
        Args:
            llm: The tensorrt_llm LLM instance.
            tokenizer_id: HuggingFace model ID for the tokenizer.
        """
        self._llm = llm
        self._tokenizer_id = tokenizer_id
        self._shutdown = False
    
    @property
    def raw_engine(self) -> Any:
        """Access the underlying TRT-LLM engine."""
        return self._llm
    
    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
        *,
        priority: int = 0,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation using TRT-LLM's generate_async API.
        
        Note: TRT-LLM doesn't support request priorities like vLLM.
        The priority parameter is accepted for interface compatibility but ignored.
        """
        if self._shutdown:
            raise EngineNotReadyError("Engine has been shutdown")
        
        prev_text = ""
        async for chunk in self._llm.generate_async(prompt, sampling_params, streaming=True):
            output = EngineOutput.from_trt(chunk, prev_text)
            if output.text:
                prev_text = output.text
            yield output
    
    async def abort(self, request_id: str) -> None:
        """Abort a TRT-LLM generation request.
        
        Note: TRT-LLM's abort mechanism may differ from vLLM.
        This is a best-effort implementation.
        """
        # TRT-LLM may not have a direct abort API like vLLM
        # The generation will naturally stop when the async iterator is not consumed
        pass
    
    async def shutdown(self) -> None:
        """Shutdown the TRT-LLM engine."""
        self._shutdown = True
        # TRT-LLM cleanup is handled by Python garbage collection
        # No explicit shutdown method like vLLM's AsyncLLMEngine
        logger.info("TRT-LLM: engine shutdown complete")
    
    @property
    def supports_cache_reset(self) -> bool:
        """TRT-LLM does not need periodic cache reset.
        
        The KV cache uses block reuse which handles memory management
        automatically without fragmentation issues.
        """
        return False
    
    async def reset_caches(self, reason: str) -> bool:
        """No-op for TRT-LLM - cache reset not needed."""
        logger.debug("TRT-LLM: cache reset requested (reason=%s) but not supported", reason)
        return False


def _build_kv_cache_config() -> dict[str, Any]:
    """Build KV cache configuration from environment settings."""
    kv_cfg: dict[str, Any] = {}
    
    if TRT_KV_FREE_GPU_FRAC:
        with contextlib.suppress(ValueError):
            kv_cfg["free_gpu_memory_fraction"] = float(TRT_KV_FREE_GPU_FRAC)
    
    if TRT_KV_ENABLE_BLOCK_REUSE:
        kv_cfg["enable_block_reuse"] = True
    
    return kv_cfg


async def _ensure_engine() -> TRTEngine:
    """Ensure the TRT-LLM engine is initialized."""
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
        
        engine_dir = TRT_ENGINE_DIR
        if not engine_dir or not os.path.isdir(engine_dir):
            raise RuntimeError(
                f"TRT_ENGINE_DIR must point to a valid TensorRT-LLM engine directory. "
                f"Got: {engine_dir!r}"
            )
        
        logger.info("TRT-LLM: building chat engine (engine_dir=%s, tokenizer=%s)", engine_dir, CHAT_MODEL)
        
        # Import TRT-LLM lazily to avoid import errors when not using TRT
        from tensorrt_llm._tensorrt_engine import LLM
        
        kwargs: dict[str, Any] = {
            "model": engine_dir,
            "tokenizer": CHAT_MODEL,
        }
        
        kv_cfg = _build_kv_cache_config()
        if kv_cfg:
            kwargs["kv_cache_config"] = kv_cfg
        
        # Run engine loading in thread pool since it's blocking
        llm = await asyncio.to_thread(LLM, **kwargs)
        
        _ENGINE = TRTEngine(llm, CHAT_MODEL)
        logger.info("TRT-LLM: chat engine ready")
        return _ENGINE


async def get_engine() -> TRTEngine:
    """Return the singleton TRT chat engine instance."""
    return await _ensure_engine()


# Alias for compatibility with vLLM interface
get_chat_engine = get_engine


async def shutdown_engines() -> None:
    """Shut down the TRT chat engine if it has been initialized."""
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

