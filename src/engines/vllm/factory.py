"""vLLM engine singleton class definition.

This module defines the VLLMEngineSingleton class that manages the lifecycle
of the vLLM engine instance using the AsyncSingleton pattern.

The singleton instance is NOT created here - it lives in the central
registry (src/engines/registry.py). This module only defines the class.

Environment Variables:
    VLLM_USE_V1=1: Use vLLM V1 engine architecture
    VLLM_WORKER_MULTIPROC_METHOD=spawn: Use spawn instead of fork
"""

from __future__ import annotations

import logging

from src.helpers.env import env_flag
from src.config import CHAT_MODEL, DEPLOY_CHAT, CHAT_MAX_LEN, CHAT_GPU_FRAC

from .engine import VLLMEngine
from .args import make_engine_args
from ..singleton import AsyncSingleton
from .setup import configure_runtime_env
from .fallback import create_engine_with_fallback

logger = logging.getLogger(__name__)


class VLLMEngineSingleton(AsyncSingleton[VLLMEngine]):
    """Singleton manager for the vLLM engine.
    
    This class handles thread-safe, async-safe initialization of the
    vLLM engine. It validates configuration and creates the engine
    instance on first access.
    
    Usage (via registry):
        from src.engines.registry import get_engine
        engine = await get_engine()
    """
    
    async def _create_instance(self) -> VLLMEngine:
        """Create the vLLM engine instance."""
        if not DEPLOY_CHAT:
            raise RuntimeError("Chat engine requested but DEPLOY_CHAT=0")
        if not CHAT_MODEL:
            raise RuntimeError("CHAT_MODEL is not configured; cannot start chat engine")
        
        # Configure runtime environment before creating engine
        configure_runtime_env()
        
        logger.info("vLLM: building chat engine (model=%s)", CHAT_MODEL)
        engine_args = make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN)
        
        raw_engine = _create_raw_engine(engine_args)
        
        engine = VLLMEngine(raw_engine)
        logger.info("vLLM: chat engine ready")
        return engine


def _create_raw_engine(engine_args: object) -> object:
    """Create the vLLM AsyncLLMEngine with appropriate log suppression.
    
    Suppresses C++ and worker stdout/stderr unless SHOW_VLLM_LOGS is set.
    Worker processes inherit redirected fds, so their output is also suppressed.
    """
    show_vllm_logs = env_flag("SHOW_VLLM_LOGS", False)
    
    if show_vllm_logs:
        return create_engine_with_fallback(engine_args)
    
    from src.scripts.filters.vllm import SuppressedFDContext
    with SuppressedFDContext(suppress_stdout=True, suppress_stderr=True):
        return create_engine_with_fallback(engine_args)


__all__ = ["VLLMEngineSingleton"]
