"""Execution dispatch logic for validated turn plans.

Routes to the appropriate execution path based on deployment configuration:
1. DEPLOY_CHAT + DEPLOY_TOOL: Sequential tool-then-chat execution
2. DEPLOY_CHAT only: Direct chat streaming
3. DEPLOY_TOOL only: Tool classification only
"""

from __future__ import annotations

import asyncio
import logging
from src.state import TurnPlan
from typing import TYPE_CHECKING
from ...config.timeouts import TOOL_TIMEOUT_S
from ...execution.executor import run_execution
from src.runtime.dependencies import RuntimeDeps
from ...execution.tool.runner import run_toolcall
from src.handlers.websocket.errors import send_error
from ...config.websocket import WS_ERROR_TEXT_TOO_LONG
from ...execution.tool.parser import parse_tool_result
from ...execution.chat.runner import run_chat_generation
from ...execution.chat.prompt_budget import fit_chat_prompt_to_budget
from ...config import DEPLOY_CHAT, DEPLOY_TOOL, CHAT_MAX_LEN, USER_UTT_MAX_TOKENS
from ...handlers.websocket.helpers import send_toolcall, safe_send_flat, stream_chat_response

if TYPE_CHECKING:
    from fastapi import WebSocket


logger = logging.getLogger(__name__)


async def _run_sequential(ws: WebSocket, plan: TurnPlan, runtime_deps: RuntimeDeps) -> None:
    """Run sequential tool-then-chat execution."""
    if runtime_deps.chat_engine is None or runtime_deps.tool_adapter is None or runtime_deps.chat_tokenizer is None:
        raise RuntimeError("Sequential execution requires chat engine, chat tokenizer, and tool adapter")
    chat_user_utt = plan.chat_user_utt or ""
    logger.info("handle_start: sequential execution")
    await run_execution(
        ws,
        plan.state,
        plan.request_id,
        plan.static_prefix,
        plan.runtime_text,
        plan.history_messages,
        chat_user_utt,
        tool_user_utt=plan.tool_user_utt,
        history_turn_id=plan.history_turn_id,
        sampling_overrides=plan.sampling_overrides,
        apply_screen_checked_prefix=plan.apply_screen_checked_prefix,
        session_handler=runtime_deps.session_handler,
        chat_engine=runtime_deps.chat_engine,
        chat_tokenizer=runtime_deps.chat_tokenizer,
        tool_adapter=runtime_deps.tool_adapter,
    )


async def _run_chat_only(ws: WebSocket, plan: TurnPlan, runtime_deps: RuntimeDeps) -> None:
    """Run chat-only streaming execution."""
    if runtime_deps.chat_engine is None or runtime_deps.chat_tokenizer is None:
        raise RuntimeError("Chat-only execution requires chat engine and chat tokenizer")
    chat_user_utt = plan.chat_user_utt or ""
    try:
        prompt_fit = fit_chat_prompt_to_budget(
            plan.static_prefix,
            plan.runtime_text,
            plan.history_messages,
            chat_user_utt,
            runtime_deps.chat_tokenizer,
            max_prompt_tokens=CHAT_MAX_LEN,
            max_user_tokens=USER_UTT_MAX_TOKENS,
        )
    except ValueError as exc:
        await send_error(ws, code=WS_ERROR_TEXT_TOO_LONG, message=str(exc))
        return
    logger.info("handle_start: chat-only streaming")
    history_user_utt, _ = runtime_deps.session_handler.normalize_user_utterances(plan.state, prompt_fit.chat_user_utt)
    final_text = await stream_chat_response(
        ws,
        run_chat_generation(
            plan.state,
            prompt_fit.prompt,
            engine=runtime_deps.chat_engine,
            chat_tokenizer=runtime_deps.chat_tokenizer,
            request_id=plan.request_id,
            sampling_overrides=plan.sampling_overrides,
            prompt_token_count=prompt_fit.prompt_tokens,
        ),
        plan.state,
        prompt_fit.chat_user_utt,
        history_turn_id=plan.history_turn_id,
        history_user_utt=history_user_utt,
        session_handler=runtime_deps.session_handler,
    )
    logger.info("handle_start: chat-only done chars=%s", len(final_text))


async def _run_tool_only(ws: WebSocket, plan: TurnPlan, runtime_deps: RuntimeDeps) -> None:
    """Run tool-only classification execution."""
    if runtime_deps.tool_adapter is None:
        raise RuntimeError("Tool-only execution requires tool adapter")
    logger.info("handle_start: tool-only routing")
    try:
        tool_user_utt, tool_user_history = runtime_deps.session_handler.prepare_tool_turn(
            plan.state,
            plan.tool_user_utt or plan.chat_user_utt or "",
            turn_id=plan.history_turn_id,
        )
        tool_res = await asyncio.wait_for(
            run_toolcall(
                plan.state,
                tool_adapter=runtime_deps.tool_adapter,
                tool_user_utt=tool_user_utt,
                tool_user_history=tool_user_history,
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
    plan: TurnPlan,
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
