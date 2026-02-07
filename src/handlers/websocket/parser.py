"""Client payload parsing for the WebSocket handler.

All client messages must be JSON objects with the envelope:
    {"type": "...", "session_id": "...", "request_id": "...", "payload": {...}}

Raises ValueError on:
- Empty messages
- Invalid JSON
- Non-object JSON values
- Missing or invalid envelope fields
"""

from __future__ import annotations

import json
from typing import Any

from ...config.websocket import WS_KEY_PAYLOAD, WS_KEY_REQUEST_ID, WS_KEY_SESSION_ID, WS_KEY_TYPE


def parse_client_message(raw: str) -> dict[str, Any]:
    """Parse and normalize a client WebSocket message.

    Args:
        raw: Raw message string from WebSocket.

    Returns:
        Normalized message dict with envelope keys.

    Raises:
        ValueError: If message is empty, invalid JSON, or missing envelope keys.
    """
    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty message.")

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Message must be valid JSON.") from exc

    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")

    msg_type = data.get(WS_KEY_TYPE)
    session_id = data.get(WS_KEY_SESSION_ID)
    request_id = data.get(WS_KEY_REQUEST_ID)
    payload = data.get(WS_KEY_PAYLOAD)

    if not msg_type:
        raise ValueError("Missing 'type' in message.")
    if not session_id:
        raise ValueError("Missing 'session_id' in message.")
    if not request_id:
        raise ValueError("Missing 'request_id' in message.")
    if payload is None:
        raise ValueError("Missing 'payload' in message.")
    if not isinstance(payload, dict):
        raise ValueError("'payload' must be a JSON object.")

    return {
        WS_KEY_TYPE: str(msg_type).strip().lower(),
        WS_KEY_SESSION_ID: str(session_id),
        WS_KEY_REQUEST_ID: str(request_id),
        WS_KEY_PAYLOAD: payload,
    }
