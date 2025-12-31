"""TensorRT-LLM engine management for the chat engine.

This module provides the TRT-LLM engine wrapper implementing the BaseEngine interface.
Unlike vLLM, TRT-LLM uses pre-built engines and does not need periodic cache resets
due to its built-in KV cache block reuse mechanism.

Architecture:
    - TRTEngine: BaseEngine implementation wrapping TensorRT-LLM
    - Singleton pattern with async-safe initialization via _ENGINE_LOCK
    - Pre-compiled engines loaded from TRT_ENGINE_DIR

Key Differences from vLLM:
    1. No JIT compilation - engines must be pre-built
    2. No cache reset support - block reuse handles memory
    3. No request priority support
    4. Abort is best-effort (iterator abandonment)

Required Configuration:
    TRT_ENGINE_DIR: Directory containing compiled TensorRT engine
    CHAT_MODEL: HuggingFace model ID (for tokenizer)

Optional Configuration:
    TRT_KV_FREE_GPU_FRAC: GPU fraction for KV cache
    TRT_KV_ENABLE_BLOCK_REUSE: Enable cache block reuse
    TRT_BATCH_SIZE: Runtime batch size (must be <= engine's baked-in max)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any
from collections.abc import AsyncGenerator

try:
    from tensorrt_llm.executor import GenerationResult  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    GenerationResult = Any  # type: ignore[misc,assignment]

from src.config import (
    CHAT_MODEL,
    DEPLOY_CHAT,
    TRT_ENGINE_DIR,
)
from ..base import BaseEngine, EngineOutput, EngineNotReadyError
from .config import (
    build_kv_cache_config,
    read_checkpoint_model_type,
    validate_runtime_batch_size,
)

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
        self._executor = getattr(llm, "_executor", None)
        self._inflight: dict[str, GenerationResult] = {}
    
    @property
    def raw_engine(self) -> Any:
        """Access the underlying TRT-LLM engine."""
        return self._llm
    
    async def generate_stream(
        self,
        prompt: str,
        sampling_params: Any,
        request_id: str,
    ) -> AsyncGenerator[EngineOutput, None]:
        """Stream generation using TRT-LLM's generate_async API.
        
        Note: TRT-LLM doesn't support request prioritization like vLLM.
        """
        if self._shutdown:
            raise EngineNotReadyError("Engine has been shutdown")
        
        prev_text = ""
        generation = self._llm.generate_async(
            prompt,
            sampling_params,
            streaming=True,
        )

        trt_request_id = getattr(generation, "request_id", None)
        if isinstance(request_id, str) and trt_request_id is not None:
            self._inflight[request_id] = generation

        try:
            async for chunk in generation:
                output = EngineOutput.from_trt(chunk, prev_text)
                if output.text:
                    prev_text = output.text
                yield output
        finally:
            if isinstance(request_id, str):
                self._inflight.pop(request_id, None)
    
    async def abort(self, request_id: str) -> None:
        """Abort a TRT-LLM generation request.
        
        Note: TRT-LLM's abort mechanism may differ from vLLM.
        This is a best-effort implementation.
        """
        if not request_id:
            return

        pending = self._inflight.pop(request_id, None)
        trt_request_id = getattr(pending, "request_id", None)
        if trt_request_id is None:
            return

        executor = getattr(self._llm, "_executor", self._executor)
        if executor is None:
            logger.warning("TRT-LLM: executor not available for cancellation")
            return

        try:
            executor.abort_request(int(trt_request_id))
            logger.info("TRT-LLM: cancelled request_id=%s", request_id)
        except Exception:  # noqa: BLE001 - best effort abort
            logger.warning("TRT-LLM: failed to cancel request_id=%s", request_id, exc_info=True)
    
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
        
        # Validate runtime batch size against engine's baked-in max (fail early)
        validate_runtime_batch_size(engine_dir)
        
        # Read model_type from checkpoint config (TRT-LLM 1.2+ needs this for custom model names)
        model_type = read_checkpoint_model_type(engine_dir)
        if model_type:
            logger.info("TRT-LLM: detected model_type=%s from checkpoint config", model_type)
        
        logger.info("TRT-LLM: building chat engine (engine_dir=%s, tokenizer=%s)", engine_dir, CHAT_MODEL)
        
        # Import TRT-LLM lazily to avoid import errors when not using TRT
        from tensorrt_llm._tensorrt_engine import LLM
        
        kwargs: dict[str, Any] = {
            "model": engine_dir,
            "tokenizer": CHAT_MODEL,
        }
        
        # Pass model_type explicitly if available (required for custom model names in TRT-LLM 1.2+)
        if model_type:
            kwargs["model_type"] = model_type
        
        kv_cfg = build_kv_cache_config()
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


async def shutdown_engine() -> None:
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
