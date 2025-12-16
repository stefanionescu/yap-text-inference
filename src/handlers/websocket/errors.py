"""Shared response helpers for WebSocket error handling.

This module provides standardized error response formatting for WebSocket
connections. All error responses follow a consistent JSON structure:

    {
        "type": "error",
        "error_code": "authentication_failed",  # Machine-readable code
        "message": "Human-readable description",
        ...extra fields
    }

Common error codes used in the application:
    - authentication_failed: Invalid or missing API key
    - server_at_capacity: Connection limit reached  
    - missing_session_id: Start message lacks session_id
    - message_rate_limited: Too many messages per window
    - cancel_rate_limited: Too many cancel requests
    - invalid_message: Malformed JSON or missing type
    - unknown_message_type: Unrecognized message type
    - validation_error: Invalid field values
    - internal_error: Unexpected server error
"""

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
    """Send a structured error message to the client.
    
    Args:
        ws: The WebSocket connection.
        error_code: Machine-readable error identifier.
        message: Human-readable error description.
        extra: Additional fields to include in the response.
    """
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
    await send_error(ws, error_code=error_code, message=message, extra=extra)
    await ws.close(code=close_code)


