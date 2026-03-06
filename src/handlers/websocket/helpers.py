"""WebSocket streaming and communication utilities.

This module provides helper functions for safe WebSocket communication
and streaming chat responses. It handles:

1. Safe Sending:
   - Catching WebSocketDisconnect during send operations
   - Returning boolean success indicators for flow control

2. Streaming Infrastructure:
   - Forwarding async chat streams to WebSocket clients
   - Sending token/final/done message frames
   - Recording conversation history on completion

3. Task Management:
   - Launching and tracking tool requests
   - Clean task cancellation with proper await

Message Protocol:
    All messages use a flat format: {"type": "...", "status": N, ...fields}
"""

from __future__ import annotations

import json
import time
import asyncio
import logging
import contextlib
from typing import Any
from src.state import _ChatStreamState
from collections.abc import AsyncIterator
from src.state.session import SessionState
from ...config.websocket import WS_STATUS_OK
from src.telemetry.instruments import get_metrics
from fastapi import WebSocket, WebSocketDisconnect
from src.handlers.session.manager import SessionHandler
from src.telemetry.phases import record_phase_error, record_phase_latency

logger = logging.getLogger(__name__)


# ============================================================================
# Private helpers
# ============================================================================


async def _send_initial_text(
    ws: WebSocket,
    initial_text: str,
    initial_text_already_sent: bool,
    state: _ChatStreamState,
) -> None:
    if not initial_text or initial_text_already_sent:
        return
    sent = await safe_send_flat(ws, "token", text=initial_text)
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
        sent = await safe_send_flat(ws, "token", text=chunk)
        if not sent:
            state.interrupted = True
            break
        state.final_text += chunk
        state.text_visible = True


async def _send_completion_frames(ws: WebSocket, state: _ChatStreamState) -> None:
    sent_final = await safe_send_flat(ws, "final", status=WS_STATUS_OK, text=state.final_text)
    if not sent_final:
        state.interrupted = True
        return
    sent_done = await safe_send_flat(ws, "done", status=WS_STATUS_OK)
    if not sent_done:
        state.interrupted = True


def _append_history(
    session_handler: SessionHandler,
    conn_state: SessionState,
    history_user: str,
    final_text: str,
    history_turn_id: str | None,
) -> None:
    session_handler.append_history_turn(
        conn_state,
        history_user,
        final_text,
        turn_id=history_turn_id,
    )


async def _handle_empty_output(ws: WebSocket) -> None:
    logger.warning("empty model output")
    get_metrics().empty_model_output_total.add(1)
    await safe_send_flat(
        ws,
        "error",
        status=500,
        code="internal_error",
        message="Model produced no output",
    )


# ============================================================================
# Public API
# ============================================================================


def build_flat_message(msg_type: str, *, status: int | None = None, **fields: Any) -> dict[str, Any]:
    """Build a flat WebSocket message dict."""
    msg: dict[str, Any] = {"type": msg_type}
    if status is not None:
        msg["status"] = status
    for k, v in fields.items():
        if v is not None:
            msg[k] = v
    return msg


async def safe_send_text(ws: WebSocket, text: str) -> bool:
    """Send text to the client, returning False if the socket is gone."""
    try:
        await ws.send_text(text)
    except WebSocketDisconnect:
        get_metrics().disconnect_mid_stream_total.add(1)
        record_phase_error("send", "client_disconnect")
        logger.info("WebSocket disconnected while sending %s bytes", len(text))
        return False
    return True


async def safe_send_json(ws: WebSocket, payload: dict[str, Any]) -> bool:
    """Send a JSON payload, swallowing client disconnects."""
    t0 = time.perf_counter()
    sent = await safe_send_text(ws, json.dumps(payload))
    elapsed = time.perf_counter() - t0
    record_phase_latency("send", elapsed)
    get_metrics().ws_send_latency.record(elapsed)
    return sent


async def safe_send_flat(ws: WebSocket, msg_type: str, *, status: int | None = None, **fields: Any) -> bool:
    """Send a flat-format JSON message."""
    return await safe_send_json(ws, build_flat_message(msg_type, status=status, **fields))


async def send_toolcall(
    ws: WebSocket,
    tools: object,
) -> None:
    """Send a toolcall message with tool results."""
    await safe_send_flat(ws, "tool", status=WS_STATUS_OK, tools=tools)


async def cancel_task(task: asyncio.Task | None) -> None:
    """Cancel an asyncio task and await its completion."""
    if not task or task.done():
        return
    logger.info("executor: cancelling task %s", repr(task))
    task.cancel()
    with contextlib.suppress(Exception):
        await task
    logger.info("executor: cancelled task %s", repr(task))


async def stream_chat_response(
    ws: WebSocket,
    stream: AsyncIterator[str],
    conn_state: SessionState,
    chat_user_utt: str,
    *,
    initial_text: str = "",
    initial_text_already_sent: bool = True,
    history_user_utt: str | None = None,
    history_turn_id: str | None = None,
    session_handler: SessionHandler,
) -> str:
    """Stream chat chunks, emit final/done messages, and record history."""
    history_user = history_user_utt if history_user_utt is not None else chat_user_utt
    state = _ChatStreamState(
        final_text=initial_text,
        text_visible=bool(initial_text) and initial_text_already_sent,
    )

    try:
        await _send_initial_text(ws, initial_text, initial_text_already_sent, state)
        if not state.interrupted:
            await _forward_stream_chunks(ws, stream, state)
        if not state.interrupted:
            if not state.final_text:
                await _handle_empty_output(ws)
                return state.final_text
            await _send_completion_frames(ws, state)
    except asyncio.CancelledError:
        if state.text_visible:
            _append_history(session_handler, conn_state, history_user, state.final_text, history_turn_id)
        raise

    if not state.interrupted:
        _append_history(session_handler, conn_state, history_user, state.final_text, history_turn_id)
    return state.final_text


__all__ = [
    "safe_send_text",
    "safe_send_json",
    "build_flat_message",
    "safe_send_flat",
    "send_toolcall",
    "cancel_task",
    "stream_chat_response",
]
