"""Shared response helpers for WebSocket error handling.

This module provides standardized error response formatting for WebSocket
connections. All error responses use the flat format:

    {"type": "error", "status": N, "code": "...", "message": "..."}
"""

from __future__ import annotations

from fastapi import WebSocket
from .helpers import safe_send_flat
from ...config.websocket import WS_STATUS_INTERNAL, ERROR_CODE_TO_STATUS


async def send_error(
    ws: WebSocket,
    *,
    status: int | None = None,
    code: str,
    message: str,
) -> None:
    """Send a structured error message to the client.

    If status is not provided, it is looked up from ERROR_CODE_TO_STATUS
    using the code. Falls back to 500 if not found.
    """
    resolved_status = status if status is not None else ERROR_CODE_TO_STATUS.get(code, WS_STATUS_INTERNAL)
    await safe_send_flat(ws, "error", status=resolved_status, code=code, message=message)


async def reject_connection(
    ws: WebSocket,
    *,
    code: str,
    message: str,
    close_code: int,
) -> None:
    """Accept connection briefly to send an error, then close immediately."""
    await ws.accept()
    await send_error(ws, code=code, message=message)
    await ws.close(code=close_code)


__all__ = ["send_error", "reject_connection"]
