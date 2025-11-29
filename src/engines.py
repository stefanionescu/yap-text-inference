"""Engine management for vLLM chat and tool models."""

from __future__ import annotations

import os
import asyncio
import contextlib
import inspect

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")
# Use 'spawn' for multiprocessing to avoid CUDA re-initialization issues in forked subprocesses
os.environ.setdefault("VLLM_WORKER_MULTIPROC_METHOD", "spawn")

from vllm.engine.async_llm_engine import AsyncLLMEngine

from .config import (
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    TOOL_MODEL,
    TOOL_GPU_FRAC,
    TOOL_MAX_LEN,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
)
from .engine_args import make_engine_args


_chat_engine: AsyncLLMEngine | None = None
_tool_engine: AsyncLLMEngine | None = None

# Lock to prevent concurrent engine construction (but not generation)
_ENGINE_CONSTRUCTION_LOCK = asyncio.Lock()


@contextlib.contextmanager
def _awq_offline_mode():
    """Temporarily force offline flags for local AWQ model loading."""
    original_offline = os.environ.get("HF_HUB_OFFLINE")
    original_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        yield
    finally:
        if original_offline is not None:
            os.environ["HF_HUB_OFFLINE"] = original_offline
        else:
            os.environ.pop("HF_HUB_OFFLINE", None)

        if original_transformers_offline is not None:
            os.environ["TRANSFORMERS_OFFLINE"] = original_transformers_offline
        else:
            os.environ.pop("TRANSFORMERS_OFFLINE", None)


def _build_engines() -> tuple[AsyncLLMEngine | None, AsyncLLMEngine | None]:
    tool = None
    chat = None
    
    if DEPLOY_TOOL:
        tool_args = make_engine_args(TOOL_MODEL, TOOL_GPU_FRAC, TOOL_MAX_LEN, is_chat=False)
        tool = _create_engine_with_awq_handling(tool_args)
        
    if DEPLOY_CHAT:
        chat_args = make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN, is_chat=True)
        chat = _create_engine_with_awq_handling(chat_args)
        
    return chat, tool


def _create_engine_with_awq_handling(engine_args):
    """Create engine with proper AWQ local model handling."""
    # Check if this is a local AWQ model that needs offline mode
    is_local_awq = getattr(engine_args, '_is_local_awq', False)
    
    if is_local_awq:
            if hasattr(engine_args, '_is_local_awq'):
                delattr(engine_args, '_is_local_awq')
            with _awq_offline_mode():
                engine = AsyncLLMEngine.from_engine_args(engine_args)
    else:
        # Normal model loading - let HF download and cache as usual
        engine = AsyncLLMEngine.from_engine_args(engine_args)
    
    return engine


async def get_chat_engine() -> AsyncLLMEngine:
    if not DEPLOY_CHAT:
        raise RuntimeError("get_chat_engine() called but DEPLOY_CHAT is False")
    global _chat_engine, _tool_engine
    if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _chat_engine  # type: ignore[return-value]


async def get_tool_engine() -> AsyncLLMEngine:
    if not DEPLOY_TOOL:
        raise RuntimeError("get_tool_engine() called but DEPLOY_TOOL is False")
    global _chat_engine, _tool_engine
    if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _tool_engine  # type: ignore[return-value]


async def _clean_engine_caches(engine: AsyncLLMEngine) -> None:
    """Best-effort clearing of caches using the public vLLM APIs.

    AsyncLLMEngine exposes `reset_mm_cache` and `reset_prefix_cache`
    for cache invalidation starting in vLLM 0.11
    (https://docs.vllm.ai/en/v0.11.2/api/vllm/v1/engine/async_llm.html).
    We invoke whichever APIs exist to stay compatible across versions.
    """
    for method_name in ("reset_mm_cache", "reset_prefix_cache"):
        method = getattr(engine, method_name, None)
        if method is None:
            continue
        try:
            maybe_coro = method()
            if inspect.isawaitable(maybe_coro):
                await maybe_coro
        except Exception:
            # Best effort only
            pass


async def clear_all_engine_caches_on_disconnect() -> None:
    """Clear caches of any constructed engines after a client disconnects."""
    global _chat_engine, _tool_engine
    if _chat_engine is not None:
        await _clean_engine_caches(_chat_engine)
    if _tool_engine is not None:
        await _clean_engine_caches(_tool_engine)

