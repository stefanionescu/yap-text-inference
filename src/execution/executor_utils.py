"""Utilities for executors (sequential and concurrent)."""

from __future__ import annotations

import asyncio
import contextlib
import json
import uuid
from collections.abc import AsyncIterator, Awaitable

from fastapi import WebSocket

from ..engines import get_tool_engine
from ..handlers.session_handler import session_handler
from .tool_runner import run_toolcall


async def send_toolcall(ws: WebSocket, status: str, raw: object) -> None:
    await ws.send_text(json.dumps({
        "type": "toolcall",
        "status": status,
        "raw": raw,
    }))


async def flush_and_send(ws: WebSocket, buffer_text: str) -> None:
    if not buffer_text:
        return
    await ws.send_text(json.dumps({"type": "token", "text": buffer_text}))


async def cancel_task(task: asyncio.Task | None) -> None:
    if not task or task.done():
        return
    task.cancel()
    with contextlib.suppress(Exception):
        await task


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
    with contextlib.suppress(Exception):
        await (await get_tool_engine()).abort_request(req_id)


async def stream_chat_response(
    ws: WebSocket,
    stream: AsyncIterator[str],
    session_id: str,
    user_utt: str,
    *,
    initial_text: str = "",
    initial_text_already_sent: bool = True,
) -> str:
    """Stream chat chunks, emit final/done messages, and record history."""
    final_text = initial_text

    if initial_text and not initial_text_already_sent:
        await ws.send_text(json.dumps({"type": "token", "text": initial_text}))

    async for chunk in stream:
        await ws.send_text(json.dumps({"type": "token", "text": chunk}))
        final_text += chunk

    await ws.send_text(json.dumps({
        "type": "final",
        "normalized_text": final_text,
    }))
    await ws.send_text(json.dumps({"type": "done", "usage": {}}))
    session_handler.append_history_turn(session_id, user_utt, final_text)
    return final_text

