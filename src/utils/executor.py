"""Utilities for executors (sequential and concurrent)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable
from dataclasses import dataclass
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from ..handlers.session import session_handler
from ..execution.tool.tool_runner import run_toolcall

logger = logging.getLogger(__name__)


async def safe_send_text(ws: WebSocket, text: str) -> bool:
    """Send text to the client, returning False if the socket is gone."""
    try:
        await ws.send_text(text)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while sending %s bytes", len(text))
        return False
    return True


async def safe_send_json(ws: WebSocket, payload: dict[str, Any]) -> bool:
    """Send a JSON payload, swallowing client disconnects."""
    return await safe_send_text(ws, json.dumps(payload))


async def send_toolcall(ws: WebSocket, status: str, raw: object) -> None:
    await safe_send_json(ws, {
        "type": "toolcall",
        "status": status,
        "raw": raw,
    })


async def flush_and_send(ws: WebSocket, buffer_text: str) -> None:
    if not buffer_text:
        return
    await safe_send_json(ws, {"type": "token", "text": buffer_text})


async def cancel_task(task: asyncio.Task | None) -> None:
    if not task or task.done():
        return
    logger.info("executor: cancelling task %s", repr(task))
    task.cancel()
    with contextlib.suppress(Exception):
        await task
    logger.info("executor: cancelled task %s", repr(task))


def launch_tool_request(
    session_id: str,
    user_utt: str,
    history_text: str,
) -> tuple[str, Awaitable[dict]]:
    """Create a tool request coroutine and register its request id."""
    tool_req_id = f"tool-{uuid.uuid4()}"
    session_handler.set_tool_request(session_id, tool_req_id)
    tool_coro = run_toolcall(
        session_id,
        user_utt,
        history_text,
        request_id=tool_req_id,
        mark_active=False,
    )
    return tool_req_id, tool_coro


async def abort_tool_request(session_id: str) -> None:
    """Best-effort abort of an in-flight tool request for the session."""
    req_id = session_handler.get_tool_request_id(session_id)
    if not req_id:
        return
    
    # Only abort if vLLM tool engine is deployed
    from ..config import DEPLOY_TOOL_ENGINE
    if not DEPLOY_TOOL_ENGINE:
        return
    
    with contextlib.suppress(Exception):
        from ..engines import get_tool_engine

        engine = await get_tool_engine()
        await engine.abort(req_id)


@dataclass
class _ChatStreamState:
    final_text: str
    text_visible: bool
    interrupted: bool = False


async def stream_chat_response(
    ws: WebSocket,
    stream: AsyncIterator[str],
    session_id: str,
    user_utt: str,
    *,
    initial_text: str = "",
    initial_text_already_sent: bool = True,
    history_user_utt: str | None = None,
    history_turn_id: str | None = None,
) -> str:
    """Stream chat chunks, emit final/done messages, and record history."""
    history_user = history_user_utt if history_user_utt is not None else user_utt
    state = _ChatStreamState(
        final_text=initial_text,
        text_visible=bool(initial_text) and initial_text_already_sent,
    )

    try:
        await _send_initial_text(ws, initial_text, initial_text_already_sent, state)
        if not state.interrupted:
            await _forward_stream_chunks(ws, stream, state)
        if not state.interrupted:
            await _send_completion_frames(ws, state)
    except asyncio.CancelledError:
        if state.text_visible:
            _append_history(session_id, history_user, state.final_text, history_turn_id)
        raise

    if not state.interrupted:
        _append_history(session_id, history_user, state.final_text, history_turn_id)
    return state.final_text


async def _send_initial_text(
    ws: WebSocket,
    initial_text: str,
    initial_text_already_sent: bool,
    state: _ChatStreamState,
) -> None:
    if not initial_text or initial_text_already_sent:
        return
    sent = await safe_send_json(ws, {"type": "token", "text": initial_text})
    if sent:
        state.text_visible = True
    else:
        state.interrupted = True


async def _forward_stream_chunks(
    ws: WebSocket,
    stream: AsyncIterator[str],
    state: _ChatStreamState,
) -> None:
    async for chunk in stream:
        sent = await safe_send_json(ws, {"type": "token", "text": chunk})
        if not sent:
            state.interrupted = True
            break
        state.final_text += chunk
        state.text_visible = True


async def _send_completion_frames(ws: WebSocket, state: _ChatStreamState) -> None:
    sent_final = await safe_send_json(
        ws,
        {
            "type": "final",
            "normalized_text": state.final_text,
        },
    )
    if not sent_final:
        state.interrupted = True
        return
    sent_done = await safe_send_json(ws, {"type": "done", "usage": {}})
    if not sent_done:
        state.interrupted = True


def _append_history(
    session_id: str,
    history_user: str,
    final_text: str,
    history_turn_id: str | None,
) -> None:
    session_handler.append_history_turn(
        session_id,
        history_user,
        final_text,
        turn_id=history_turn_id,
    )


__all__ = [
    "safe_send_text",
    "safe_send_json",
    "send_toolcall",
    "flush_and_send",
    "cancel_task",
    "launch_tool_request",
    "abort_tool_request",
    "stream_chat_response",
]