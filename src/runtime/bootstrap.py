"""Runtime dependency bootstrap.

This module eagerly builds all configured runtime services at startup.
Request handlers consume these dependencies directly instead of triggering
lazy singleton initialization at request time.
"""

from __future__ import annotations

import asyncio
from .dependencies import RuntimeDeps
from src.tokens.tokenizer import FastTokenizer
from src.tool.factory import create_tool_adapter
from src.handlers.connections import ConnectionHandler
from src.handlers.session.manager import SessionHandler
from src.config import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL, INFERENCE_ENGINE


async def _build_chat_engine():
    if not DEPLOY_CHAT:
        return None
    if INFERENCE_ENGINE not in {"vllm", "trt"}:
        raise RuntimeError(f"Unsupported chat inference engine: {INFERENCE_ENGINE!r}")
    if INFERENCE_ENGINE == "vllm":
        from src.engines.vllm.factory import create_vllm_engine  # noqa: PLC0415

        return await create_vllm_engine()
    from src.engines.trt.factory import create_trt_engine  # noqa: PLC0415

    return await create_trt_engine()


async def _build_chat_tokenizer() -> FastTokenizer | None:
    if not DEPLOY_CHAT:
        return None
    if not CHAT_MODEL:
        raise RuntimeError("CHAT_MODEL is required when DEPLOY_CHAT is enabled")
    return await asyncio.to_thread(FastTokenizer, CHAT_MODEL)


async def _build_tool_tokenizer() -> FastTokenizer | None:
    if not DEPLOY_TOOL:
        return None
    if not TOOL_MODEL:
        raise RuntimeError("TOOL_MODEL is required when DEPLOY_TOOL is enabled")
    return await asyncio.to_thread(FastTokenizer, TOOL_MODEL)


async def _build_tool_adapter():
    if not DEPLOY_TOOL:
        return None
    return await asyncio.to_thread(create_tool_adapter)


async def build_runtime_deps() -> RuntimeDeps:
    """Build runtime dependencies eagerly for configured deployment modes."""
    chat_engine, chat_tokenizer, tool_tokenizer, tool_adapter = await asyncio.gather(
        _build_chat_engine(),
        _build_chat_tokenizer(),
        _build_tool_tokenizer(),
        _build_tool_adapter(),
    )

    tool_history_budget = tool_adapter.max_history_tokens if tool_adapter else None
    tool_input_budget = tool_adapter.max_input_tokens if tool_adapter else None
    session_handler = SessionHandler(
        chat_engine=chat_engine,
        tool_history_budget=tool_history_budget,
        tool_input_budget=tool_input_budget,
        chat_tokenizer=chat_tokenizer,
        tool_tokenizer=tool_tokenizer,
    )
    connections = ConnectionHandler()
    cache_reset_manager = None
    if chat_engine is not None and chat_engine.supports_cache_reset:
        from src.engines.vllm.cache import CacheResetManager  # noqa: PLC0415

        cache_reset_manager = CacheResetManager()

    return RuntimeDeps(
        connections=connections,
        session_handler=session_handler,
        chat_engine=chat_engine,
        cache_reset_manager=cache_reset_manager,
        tool_adapter=tool_adapter,
        chat_tokenizer=chat_tokenizer,
        tool_tokenizer=tool_tokenizer,
    )


__all__ = [
    "build_runtime_deps",
]
