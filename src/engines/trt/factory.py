"""TRT-LLM engine singleton and factory functions.

This module manages the lifecycle of the TRT-LLM engine instance using
the AsyncSingleton pattern for thread-safe initialization.

Factory Functions:
    get_engine(): Return the singleton TRT engine instance
    shutdown_engine(): Clean shutdown of the engine

Required Configuration:
    TRT_ENGINE_DIR: Directory containing compiled TensorRT engine
    CHAT_MODEL: HuggingFace model ID (for tokenizer)

Optional Configuration:
    TRT_KV_FREE_GPU_FRAC: GPU fraction for KV cache
    TRT_BATCH_SIZE: Runtime batch size (must be <= engine's baked-in max)
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

from src.config import CHAT_MODEL, DEPLOY_CHAT, TRT_ENGINE_DIR
from src.helpers.env import env_flag

from ..singleton import AsyncSingleton
from .engine import TRTEngine
from .setup import (
    build_kv_cache_config,
    read_checkpoint_model_type,
    validate_runtime_batch_size,
)

logger = logging.getLogger(__name__)


class _TRTEngineSingleton(AsyncSingleton[TRTEngine]):
    """Singleton manager for the TRT-LLM engine."""
    
    async def _create_instance(self) -> TRTEngine:
        """Create the TRT-LLM engine instance."""
        if not DEPLOY_CHAT:
            raise RuntimeError("Chat engine requested but DEPLOY_CHAT=0")
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
        
        llm = await _create_llm_instance(kwargs)
        
        engine = TRTEngine(llm, CHAT_MODEL)
        logger.info("TRT-LLM: chat engine ready")
        return engine


async def _create_llm_instance(kwargs: dict[str, Any]) -> Any:
    """Create the TRT-LLM LLM instance with appropriate log suppression.
    
    Suppresses C++ stdout/stderr unless SHOW_TRT_LOGS is set. TRT-LLM's C++
    code writes directly to file descriptors, bypassing Python's logging.
    """
    show_trt_logs = env_flag("SHOW_TRT_LOGS", False)
    
    from src.scripts.filters.trt import configure_trt_logger, SuppressedFDContext
    
    if show_trt_logs:
        configure_trt_logger()
        from tensorrt_llm._tensorrt_engine import LLM
        return await asyncio.to_thread(LLM, **kwargs)
    
    with SuppressedFDContext(suppress_stdout=True, suppress_stderr=True):
        configure_trt_logger()
        from tensorrt_llm._tensorrt_engine import LLM
        return await asyncio.to_thread(LLM, **kwargs)


_engine_singleton = _TRTEngineSingleton()


async def get_engine() -> TRTEngine:
    """Return the singleton TRT chat engine instance."""
    return await _engine_singleton.get()


async def shutdown_engine() -> None:
    """Shut down the TRT chat engine if it has been initialized."""
    await _engine_singleton.shutdown()


__all__ = [
    "get_engine",
    "shutdown_engine",
]

