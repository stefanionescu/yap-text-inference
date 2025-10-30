"""Utilities for executors (sequential and concurrent)."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Optional
from fastapi import WebSocket


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


async def cancel_task(task: Optional[asyncio.Task]) -> None:
    if not task:
        return
    if task.done():
        return
    task.cancel()
    with contextlib.suppress(Exception):
        await task


