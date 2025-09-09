from __future__ import annotations

from typing import Tuple

from vllm.engine.async_llm_engine import AsyncLLMEngine

from .config import (
    CHAT_GPU_FRAC,
    CHAT_MAX_LEN,
    CHAT_MODEL,
    TOOL_MODEL,
    TOOL_GPU_FRAC,
    make_engine_args,
)


_chat_engine: AsyncLLMEngine | None = None
_tool_engine: AsyncLLMEngine | None = None


def _build_engines() -> Tuple[AsyncLLMEngine, AsyncLLMEngine]:
    tool = AsyncLLMEngine.from_engine_args(
        make_engine_args(TOOL_MODEL, TOOL_GPU_FRAC, 1024, is_chat=False)
    )
    chat = AsyncLLMEngine.from_engine_args(
        make_engine_args(CHAT_MODEL, CHAT_GPU_FRAC, CHAT_MAX_LEN, is_chat=True)
    )
    return chat, tool


def get_chat_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or _tool_engine is None:
        _chat, _tool = _build_engines()
        _chat_engine, _tool_engine = _chat, _tool
    return _chat_engine  # type: ignore[return-value]


def get_tool_engine() -> AsyncLLMEngine:
    global _chat_engine, _tool_engine
    if _chat_engine is None or _tool_engine is None:
        _chat, _tool = _build_engines()
        _chat_engine, _tool_engine = _chat, _tool
    return _tool_engine  # type: ignore[return-value]


