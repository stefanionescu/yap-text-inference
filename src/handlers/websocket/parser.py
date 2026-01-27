"""Client payload parsing for the WebSocket handler.

This module handles parsing and normalization of incoming WebSocket messages.
It supports two formats:

1. Sentinel Strings:
   - "CANCEL" -> {"type": "cancel"}
   - "END" -> {"type": "end"}
   
2. JSON Objects:
   - Must contain "type" field (or legacy "cancel"/"end" boolean flags)
   - Type is normalized to lowercase
   - request_id is stringified if present

The parser provides consistent internal message format regardless of
the client's chosen format, allowing handlers to work with a uniform
dict structure.

Raises ValueError on:
- Empty messages
- Invalid JSON
- Non-object JSON values
- Missing type field
"""

from __future__ import annotations

import json
from typing import Any

from ...config.websocket import WS_END_SENTINEL, WS_CANCEL_SENTINEL


def parse_client_message(raw: str) -> dict[str, Any]:
    """Parse and normalize a client WebSocket message.
    
    Handles both sentinel strings (CANCEL, END) and JSON objects.
    Normalizes message type to lowercase and ensures consistent format.
    
    Args:
        raw: Raw message string from WebSocket.
        
    Returns:
        Normalized message dict with "type" field.
        
    Raises:
        ValueError: If message is empty, invalid JSON, or missing type.
    """

    text = (raw or "").strip()
    if not text:
        raise ValueError("Empty message.")

    if text == WS_CANCEL_SENTINEL:
        return {"type": "cancel"}
    if text == WS_END_SENTINEL:
        return {"type": "end"}

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("Message must be valid JSON or a sentinel string.") from exc

    if not isinstance(data, dict):
        raise ValueError("Message must be a JSON object.")

    msg_type = data.get("type")
    if not msg_type:
        if bool(data.get("cancel")):
            msg_type = "cancel"
        elif bool(data.get("end")):
            msg_type = "end"

    if not msg_type:
        raise ValueError("Missing 'type' in message.")

    data["type"] = str(msg_type).strip().lower()
    if "request_id" in data and data["request_id"] is not None:
        data["request_id"] = str(data["request_id"])
    return data


