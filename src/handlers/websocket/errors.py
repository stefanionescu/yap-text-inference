"""Shared response helpers for WebSocket error handling."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket


async def send_error(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    extra: dict[str, Any] | None = None,
) -> None:
    payload: dict[str, Any] = {
        "type": "error",
        "error_code": error_code,
        "message": message,
    }
    if extra:
        payload.update(extra)
    await ws.send_text(json.dumps(payload))


async def reject_connection(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    close_code: int,
    extra: dict[str, Any] | None = None,
) -> None:
    await ws.accept()
    await send_error(ws, error_code=error_code, message=message, extra=extra)
    await ws.close(code=close_code)


