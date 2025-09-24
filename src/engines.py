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
    make_engine_args,
)


_chat_engine: AsyncLLMEngine | None = None
_tool_engine: AsyncLLMEngine | None = None

# Lock to prevent concurrent engine construction (but not generation)
_ENGINE_CONSTRUCTION_LOCK = asyncio.Lock()


def _build_engines() -> Tuple[AsyncLLMEngine, AsyncLLMEngine]:
    tool = AsyncLLMEngine.from_engine_args(
        make_engine_args(TOOL_MODEL, TOOL_GPU_FRAC, TOOL_MAX_LEN, is_chat=False)
    )
    chat = AsyncLLMEngine.from_engine_args(
        make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN, is_chat=True)
    )
    return chat, tool


async def get_chat_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or _tool_engine is None:
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if _chat_engine is None or _tool_engine is None:
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _chat_engine  # type: ignore[return-value]


async def get_tool_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or _tool_engine is None:
        async with _ENGINE_CONSTRUCTION_LOCK:
            # Double-check pattern to avoid building engines twice
            if _chat_engine is None or _tool_engine is None:
                _chat, _tool = _build_engines()
                _chat_engine, _tool_engine = _chat, _tool
    return _tool_engine  # type: ignore[return-value]


