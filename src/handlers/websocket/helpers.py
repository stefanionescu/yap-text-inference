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
   - Launching and tracking tool/classifier requests
   - Clean task cancellation with proper await

Message Protocol:
    Token frame:   {"type": "token", "text": "chunk"}
    Final frame:   {"type": "final", "normalized_text": "full response"}
    Done frame:    {"type": "done", "usage": {...}}
    Toolcall:      {"type": "toolcall", "status": "...", "raw": {...}}
"""

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

from ..session import session_handler
from ...execution.tool.runner import run_toolcall

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


async def send_toolcall(ws: WebSocket, status: str, raw: object) -> None:
    """Send a toolcall message with status and raw result data.
    
    Args:
        ws: The WebSocket connection.
        status: Tool call status (e.g., "completed", "error").
        raw: Raw tool result data to include.
    """
    await safe_send_json(ws, {
        "type": "toolcall",
        "status": status,
        "raw": raw,
    })


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


def launch_tool_request(
    session_id: str,
    user_utt: str,
) -> tuple[str, Awaitable[dict]]:
    """Create a tool request coroutine and register its request ID.
    
    Generates a unique request ID, registers it with the session handler,
    and creates an asyncio task for the tool call.
    
    Args:
        session_id: The session to associate the request with.
        user_utt: The user's utterance to classify.
        
    Returns:
        Tuple of (request_id, asyncio.Task) for the tool call.
    """
    tool_req_id = f"tool-{uuid.uuid4()}"
    session_handler.set_tool_request(session_id, tool_req_id)
    tool_task = asyncio.create_task(
        run_toolcall(
            session_id,
            user_utt,
            request_id=tool_req_id,
            mark_active=False,
        )
    )
    return tool_req_id, tool_task


@dataclass
class _ChatStreamState:
    """Internal state for stream_chat_response."""
    final_text: str      # Accumulated response text
    text_visible: bool   # Whether any text has been sent to client
    interrupted: bool = False  # Whether streaming was interrupted


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
    "cancel_task",
    "launch_tool_request",
    "stream_chat_response",
]
