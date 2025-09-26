"""Engine management for vLLM chat and tool models."""

from __future__ import annotations

import os
import asyncio
import logging
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
    """Build engines with reduced logging and summary at end."""
    logger = logging.getLogger(__name__)
    
    # Temporarily suppress vLLM's verbose logging during construction
    vllm_logger = logging.getLogger("vllm")
    original_level = vllm_logger.level
    vllm_logger.setLevel(logging.WARNING)
    
    try:
        tool = None
        chat = None
        
        if DEPLOY_TOOL:
            logger.info(f"Loading tool model: {TOOL_MODEL}")
            tool = AsyncLLMEngine.from_engine_args(
                make_engine_args(TOOL_MODEL, TOOL_GPU_FRAC, TOOL_MAX_LEN, is_chat=False)
            )
        
        if DEPLOY_CHAT:
            logger.info(f"Loading chat model: {CHAT_MODEL}")
            chat = AsyncLLMEngine.from_engine_args(
                make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN, is_chat=True)
            )
        
        # Log deployment summary
        _log_deployment_summary(chat, tool)
        
        return chat, tool
    
    finally:
        # Restore original vLLM logging level
        vllm_logger.setLevel(original_level)


def _log_deployment_summary(chat_engine: AsyncLLMEngine | None, tool_engine: AsyncLLMEngine | None) -> None:
    """Log a summary of deployed models and their capacities."""
    logger = logging.getLogger(__name__)
    
    deployed = []
    if chat_engine:
        deployed.append(f"Chat: {CHAT_MODEL} ({CHAT_GPU_FRAC:.0%} GPU)")
    if tool_engine:
        deployed.append(f"Tool: {TOOL_MODEL} ({TOOL_GPU_FRAC:.0%} GPU)")
    
    logger.info("=" * 60)
    logger.info(f"Deployment ready: {', '.join(deployed)}")
    
    # Try to get KV cache info if available
    try:
        if chat_engine and hasattr(chat_engine, 'engine'):
            # Access engine stats if available in V1
            logger.info("Chat engine ready for inference")
        if tool_engine and hasattr(tool_engine, 'engine'):
            logger.info("Tool engine ready for inference")
    except Exception:
        pass  # Don't fail on stats access
    
    logger.info("=" * 60)


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


