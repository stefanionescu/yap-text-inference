"""Engine management for vLLM chat and tool models."""

from __future__ import annotations

import os
import asyncio
from typing import Tuple

# Ensure V1 engine path before importing vLLM
os.environ.setdefault("VLLM_USE_V1", "1")

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
    make_engine_args,
)


_chat_engine: AsyncLLMEngine | None = None
_tool_engine: AsyncLLMEngine | None = None

# Lock to prevent concurrent engine construction (but not generation)
_ENGINE_CONSTRUCTION_LOCK = asyncio.Lock()


def _build_engines() -> Tuple[AsyncLLMEngine | None, AsyncLLMEngine | None]:
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
        # Store original values
        original_offline = os.environ.get("HF_HUB_OFFLINE")
        original_transformers_offline = os.environ.get("TRANSFORMERS_OFFLINE")
        
        # Set offline mode for local AWQ models
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        
        try:
            # Remove the internal flag before passing to vLLM
            if hasattr(engine_args, '_is_local_awq'):
                delattr(engine_args, '_is_local_awq')
            engine = AsyncLLMEngine.from_engine_args(engine_args)
        finally:
            # Restore original values
            if original_offline is not None:
                os.environ["HF_HUB_OFFLINE"] = original_offline
            else:
                os.environ.pop("HF_HUB_OFFLINE", None)
                
            if original_transformers_offline is not None:
                os.environ["TRANSFORMERS_OFFLINE"] = original_transformers_offline
            else:
                os.environ.pop("TRANSFORMERS_OFFLINE", None)
    else:
        # Normal model loading - let HF download and cache as usual
        engine = AsyncLLMEngine.from_engine_args(engine_args)
    
    return engine


async def get_chat_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if _chat_engine is None or (_tool_engine is None and DEPLOY_TOOL):
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _chat_engine  # type: ignore[return-value]


async def get_tool_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if (_chat_engine is None and DEPLOY_CHAT) or _tool_engine is None:
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _tool_engine  # type: ignore[return-value]

