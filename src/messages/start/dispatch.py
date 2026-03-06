"""Execution dispatch logic for start messages.

Routes to the appropriate execution path based on deployment configuration:
1. DEPLOY_CHAT + DEPLOY_TOOL: Sequential tool-then-chat execution
2. DEPLOY_CHAT only: Direct chat streaming
3. DEPLOY_TOOL only: Tool classification only
"""

from __future__ import annotations

import asyncio
import logging
from src.state import StartPlan
from typing import TYPE_CHECKING
from ...config.timeouts import TOOL_TIMEOUT_S
from ...config import DEPLOY_CHAT, DEPLOY_TOOL
from ...execution.executor import run_execution
from src.runtime.dependencies import RuntimeDeps
from ...execution.tool.runner import run_toolcall
from ...execution.tool.parser import parse_tool_result
from ...execution.chat.runner import run_chat_generation
from ...handlers.websocket.helpers import send_toolcall, safe_send_flat, stream_chat_response

if TYPE_CHECKING:
    from fastapi import WebSocket


logger = logging.getLogger(__name__)


async def _run_sequential(ws: WebSocket, plan: StartPlan, runtime_deps: RuntimeDeps) -> None:
    """Run sequential tool-then-chat execution."""
    if runtime_deps.chat_engine is None or runtime_deps.tool_adapter is None or runtime_deps.chat_tokenizer is None:
        raise RuntimeError("Sequential execution requires chat engine, chat tokenizer, and tool adapter")
    logger.info("handle_start: sequential execution")
    await run_execution(
        ws,
        plan.state,
        plan.request_id,
        plan.static_prefix,
        plan.runtime_text,
        plan.history_turns,
        plan.user_utt,
        history_turn_id=plan.history_turn_id,
        sampling_overrides=plan.sampling_overrides,
        session_handler=runtime_deps.session_handler,
        chat_engine=runtime_deps.chat_engine,
        chat_tokenizer=runtime_deps.chat_tokenizer,
        tool_adapter=runtime_deps.tool_adapter,
    )


async def _run_chat_only(ws: WebSocket, plan: StartPlan, runtime_deps: RuntimeDeps) -> None:
    """Run chat-only streaming execution."""
    if runtime_deps.chat_engine is None or runtime_deps.chat_tokenizer is None:
        raise RuntimeError("Chat-only execution requires chat engine and chat tokenizer")
    logger.info("handle_start: chat-only streaming")
    final_text = await stream_chat_response(
        ws,
        run_chat_generation(
            plan.state,
            plan.static_prefix,
            plan.runtime_text,
            plan.history_turns,
            plan.user_utt,
            engine=runtime_deps.chat_engine,
            session_handler=runtime_deps.session_handler,
            chat_tokenizer=runtime_deps.chat_tokenizer,
            request_id=plan.request_id,
            sampling_overrides=plan.sampling_overrides,
        ),
        plan.state,
        plan.user_utt,
        history_turn_id=plan.history_turn_id,
        history_user_utt=plan.user_utt,
        session_handler=runtime_deps.session_handler,
    )
    logger.info("handle_start: chat-only done chars=%s", len(final_text))


async def _run_tool_only(ws: WebSocket, plan: StartPlan, runtime_deps: RuntimeDeps) -> None:
    """Run tool-only classification execution."""
    if runtime_deps.tool_adapter is None:
        raise RuntimeError("Tool-only execution requires tool adapter")
    logger.info("handle_start: tool-only routing")
    try:
        tool_res = await asyncio.wait_for(
            run_toolcall(
                plan.state,
                session_handler=runtime_deps.session_handler,
                tool_adapter=runtime_deps.tool_adapter,
                mark_active=False,
            ),
            timeout=TOOL_TIMEOUT_S,
        )
    except TimeoutError:
        logger.warning("handle_start: tool-only timeout timeout_s=%.1f", TOOL_TIMEOUT_S)
        tool_res = {"cancelled": True, "text": "[]", "timeout": True}

    raw_field, is_tool = parse_tool_result(tool_res)
    tools = raw_field if is_tool else []
    await send_toolcall(ws, tools)
    await safe_send_flat(ws, "final", status=200, text="")
    await safe_send_flat(ws, "done", status=200)
    logger.info("handle_start: tool-only done is_tool=%s", is_tool)


async def dispatch_execution(
    ws: WebSocket,
    plan: StartPlan,
    runtime_deps: RuntimeDeps,
) -> None:
    """Dispatch execution based on deployment configuration."""
    if DEPLOY_CHAT and DEPLOY_TOOL:
        await _run_sequential(ws, plan, runtime_deps)
    elif DEPLOY_CHAT and not DEPLOY_TOOL:
        await _run_chat_only(ws, plan, runtime_deps)
    elif DEPLOY_TOOL and not DEPLOY_CHAT:
        await _run_tool_only(ws, plan, runtime_deps)


__all__ = ["dispatch_execution"]
