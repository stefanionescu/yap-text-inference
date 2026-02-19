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
    All messages use a standard envelope:
        {"type": "...", "session_id": "...", "request_id": "...", "payload": {...}}
"""

from __future__ import annotations

import json
import asyncio
import logging
import contextlib
from typing import Any
from collections.abc import AsyncIterator

from fastapi import WebSocket, WebSocketDisconnect

from src.state import _ChatStreamState
from src.handlers.session.manager import SessionHandler

from ...config.websocket import WS_KEY_TYPE, WS_KEY_PAYLOAD, WS_KEY_REQUEST_ID, WS_KEY_SESSION_ID

logger = logging.getLogger(__name__)


async def safe_send_text(ws: WebSocket, text: str) -> bool:
    """Send text to the client, returning False if the socket is gone.

    Catches WebSocketDisconnect to allow graceful handling of
    client disconnections during send operations.

    Args:
        ws: The WebSocket connection.
        text: Raw text to send.

    Returns:
        True if sent successfully, False if client disconnected.
    """
    try:
        await ws.send_text(text)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected while sending %s bytes", len(text))
        return False
    return True


async def safe_send_json(ws: WebSocket, payload: dict[str, Any]) -> bool:
    """Send a JSON payload, swallowing client disconnects.

    Args:
        ws: The WebSocket connection.
        payload: Dictionary to serialize and send.

    Returns:
        True if sent successfully, False if client disconnected.
    """
    return await safe_send_text(ws, json.dumps(payload))


def build_envelope(
    msg_type: str,
    session_id: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a standardized WebSocket message envelope."""
    return {
        WS_KEY_TYPE: msg_type,
        WS_KEY_SESSION_ID: session_id,
        WS_KEY_REQUEST_ID: request_id,
        WS_KEY_PAYLOAD: payload or {},
    }


async def safe_send_envelope(
    ws: WebSocket,
    *,
    msg_type: str,
    session_id: str,
    request_id: str,
    payload: dict[str, Any] | None = None,
) -> bool:
    """Send an envelope-wrapped JSON payload."""
    return await safe_send_json(ws, build_envelope(msg_type, session_id, request_id, payload))


async def send_toolcall(
    ws: WebSocket,
    session_id: str,
    request_id: str,
    status: str,
    raw: object,
) -> None:
    """Send a toolcall message with status and raw result data.

    Args:
        ws: The WebSocket connection.
        status: Tool call status (e.g., "completed", "error").
        raw: Raw tool result data to include.
    """
    await safe_send_envelope(
        ws,
        msg_type="toolcall",
        session_id=session_id,
        request_id=request_id,
        payload={
            "status": status,
            "raw": raw,
        },
    )


async def cancel_task(task: asyncio.Task | None) -> None:
    """Cancel an asyncio task and await its completion.

    Safely handles None tasks and already-completed tasks.
    Suppresses all exceptions during cancellation.

    Args:
        task: The task to cancel, or None.
    """
    if not task or task.done():
        return
    logger.info("executor: cancelling task %s", repr(task))
    task.cancel()
    with contextlib.suppress(Exception):
        await task
    logger.info("executor: cancelled task %s", repr(task))


async def _send_initial_text(
    ws: WebSocket,
    initial_text: str,
    initial_text_already_sent: bool,
    state: _ChatStreamState,
) -> None:
    if not initial_text or initial_text_already_sent:
        return
    sent = await safe_send_envelope(
        ws,
        msg_type="token",
        session_id=state.session_id,
        request_id=state.request_id,
        payload={"text": initial_text},
    )
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
        sent = await safe_send_envelope(
            ws,
            msg_type="token",
            session_id=state.session_id,
            request_id=state.request_id,
            payload={"text": chunk},
        )
        if not sent:
            state.interrupted = True
            break
        state.final_text += chunk
        state.text_visible = True


async def _send_completion_frames(ws: WebSocket, state: _ChatStreamState) -> None:
    sent_final = await safe_send_envelope(
        ws,
        msg_type="final",
        session_id=state.session_id,
        request_id=state.request_id,
        payload={"normalized_text": state.final_text},
    )
    if not sent_final:
        state.interrupted = True
        return
    sent_done = await safe_send_envelope(
        ws,
        msg_type="done",
        session_id=state.session_id,
        request_id=state.request_id,
        payload={"usage": {}},
    )
    if not sent_done:
        state.interrupted = True


def _append_history(
    session_handler: SessionHandler,
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


async def _handle_empty_output(
    ws: WebSocket,
    session_id: str,
    request_id: str,
) -> None:
    logger.warning("empty model output: session_id=%s request_id=%s", session_id, request_id)
    await safe_send_envelope(
        ws,
        msg_type="error",
        session_id=session_id,
        request_id=request_id,
        payload={
            "code": "internal_error",
            "message": "Model produced no output",
            "details": {"reason_code": "empty_model_output"},
        },
    )


async def stream_chat_response(
    ws: WebSocket,
    stream: AsyncIterator[str],
    session_id: str,
    request_id: str,
    user_utt: str,
    *,
    initial_text: str = "",
    initial_text_already_sent: bool = True,
    history_user_utt: str | None = None,
    history_turn_id: str | None = None,
    session_handler: SessionHandler,
) -> str:
    """Stream chat chunks, emit final/done messages, and record history.

    This is the main function for sending streaming chat responses to clients.
    It handles:
    - Optional initial text (e.g., screenshot analysis prefix)
    - Forwarding stream chunks as token frames
    - Sending final and done completion frames
    - Recording the conversation turn in session history
    - Proper cleanup on cancellation or disconnection

    Args:
        ws: The WebSocket connection.
        stream: Async iterator yielding text chunks from the chat model.
        session_id: Session for history recording.
        request_id: Request identifier for outbound messages.
        user_utt: User utterance (for logging/tracking).
        initial_text: Optional prefix text to include in response.
        initial_text_already_sent: Whether initial_text was already sent to client.
        history_user_utt: Override user text for history (if different from user_utt).
        history_turn_id: Existing turn ID to update (for streaming updates).

    Returns:
        The complete response text (initial_text + all stream chunks).
    """
    history_user = history_user_utt if history_user_utt is not None else user_utt
    state = _ChatStreamState(
        final_text=initial_text,
        text_visible=bool(initial_text) and initial_text_already_sent,
        session_id=session_id,
        request_id=request_id,
    )

    try:
        await _send_initial_text(ws, initial_text, initial_text_already_sent, state)
        if not state.interrupted:
            await _forward_stream_chunks(ws, stream, state)
        if not state.interrupted:
            if not state.final_text:
                await _handle_empty_output(ws, session_id, request_id)
                return state.final_text
            await _send_completion_frames(ws, state)
    except asyncio.CancelledError:
        if state.text_visible:
            _append_history(session_handler, session_id, history_user, state.final_text, history_turn_id)
        raise

    if not state.interrupted:
        _append_history(session_handler, session_id, history_user, state.final_text, history_turn_id)
    return state.final_text


__all__ = [
    "safe_send_text",
    "safe_send_json",
    "build_envelope",
    "safe_send_envelope",
    "send_toolcall",
    "cancel_task",
    "stream_chat_response",
]
