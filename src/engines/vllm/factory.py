"""vLLM engine singleton and factory functions.

This module manages the lifecycle of the vLLM engine instance using
the AsyncSingleton pattern for thread-safe initialization.

Factory Functions:
    get_engine(): Return the singleton vLLM engine instance
    shutdown_engine(): Clean shutdown of the engine
    reset_engine_caches(): Reset prefix/MM caches with rate limiting
    clear_caches_on_disconnect(): Force cache reset on client disconnect

Environment Variables:
    VLLM_USE_V1=1: Use vLLM V1 engine architecture
    VLLM_WORKER_MULTIPROC_METHOD=spawn: Use spawn instead of fork
"""

from __future__ import annotations

import logging

from src.config import CHAT_GPU_FRAC, CHAT_MAX_LEN, CHAT_MODEL, DEPLOY_CHAT
from src.helpers.env import env_flag

from ..singleton import AsyncSingleton
from .args import make_engine_args
from .cache import try_reset_caches
from .engine import VLLMEngine
from .fallback import create_engine_with_fallback
from .setup import configure_runtime_env

logger = logging.getLogger(__name__)


class _VLLMEngineSingleton(AsyncSingleton[VLLMEngine]):
    """Singleton manager for the vLLM engine."""
    
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


_engine_singleton = _VLLMEngineSingleton()


async def get_engine() -> VLLMEngine:
    """Return the singleton chat engine instance."""
    return await _engine_singleton.get()


async def shutdown_engine() -> None:
    """Shut down the chat engine if it has been initialized."""
    await _engine_singleton.shutdown()


async def reset_engine_caches(reason: str, *, force: bool = False) -> bool:
    """Reset prefix/MM caches if interval elapsed (or force).
    
    Args:
        reason: Human-readable reason for the reset.
        force: Force reset even if interval hasn't elapsed.
        
    Returns:
        True if caches were reset, False otherwise.
    """
    if not _engine_singleton.is_initialized:
        return False
    
    engine = await _engine_singleton.get()
    return await try_reset_caches(engine, reason, force=force)


async def clear_caches_on_disconnect() -> None:
    """Force cache reset when all clients disconnect."""
    await reset_engine_caches("all_clients_disconnected", force=True)


__all__ = [
    "clear_caches_on_disconnect",
    "get_engine",
    "reset_engine_caches",
    "shutdown_engine",
]

