"""Shared response helpers for WebSocket error handling.

This module provides standardized error response formatting for WebSocket
connections. All error responses follow the standard envelope:

    {
        "type": "error",
        "session_id": "...",
        "request_id": "...",
        "payload": {"code": "...", "message": "...", "details": {...}}
    }

Common error codes used in the application:
    - authentication_failed: Invalid or missing API key
    - server_at_capacity: Connection limit reached
    - invalid_message: Malformed JSON or missing type
    - invalid_payload: Missing or invalid fields
    - invalid_settings: Unsupported configuration for this request
    - rate_limited: Rate limit exceeded
    - internal_error: Unexpected server error
"""

from __future__ import annotations

from typing import Any

from fastapi import WebSocket

from ...config.websocket import WS_UNKNOWN_REQUEST_ID, WS_UNKNOWN_SESSION_ID
from .helpers import safe_send_envelope


def build_error_payload(
    code: str,
    message: str,
    *,
    details: dict[str, Any] | None = None,
    reason_code: str | None = None,
) -> dict[str, Any]:
    """Build a standardized error payload with optional details."""
    payload_details = dict(details or {})
    if reason_code:
        payload_details.setdefault("reason_code", reason_code)
    return {
        "code": code,
        "message": message,
        "details": payload_details,
    }


async def send_error(
    ws: WebSocket,
    *,
    session_id: str | None = None,
    request_id: str | None = None,
    error_code: str,
    message: str,
    details: dict[str, Any] | None = None,
    reason_code: str | None = None,
) -> None:
    """Send a structured error message to the client."""
    sid = session_id or WS_UNKNOWN_SESSION_ID
    rid = request_id or WS_UNKNOWN_REQUEST_ID
    payload = build_error_payload(
        error_code,
        message,
        details=details,
        reason_code=reason_code,
    )
    await safe_send_envelope(
        ws,
        msg_type="error",
        session_id=sid,
        request_id=rid,
        payload=payload,
    )


async def reject_connection(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    close_code: int,
    details: dict[str, Any] | None = None,
    reason_code: str | None = None,
) -> None:
    """Accept connection briefly to send an error, then close immediately.

    This pattern ensures the client receives a meaningful error message
    rather than just a raw close code. The connection is accepted, the
    error is sent, and then immediately closed.

    Args:
        ws: The WebSocket connection to reject.
        error_code: Machine-readable error identifier.
        message: Human-readable rejection reason.
        close_code: WebSocket close code (e.g., 4001 unauthorized, 4003 busy).
        extra: Additional fields for the error response.
    """
    await ws.accept()
    await send_error(
        ws,
        session_id=WS_UNKNOWN_SESSION_ID,
        request_id=WS_UNKNOWN_REQUEST_ID,
        error_code=error_code,
        message=message,
        details=details,
        reason_code=reason_code,
    )
    await ws.close(code=close_code)
