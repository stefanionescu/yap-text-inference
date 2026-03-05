"""Client payload parsing for the WebSocket handler.

All client messages must be JSON objects with at minimum:
    {"type": "..."}
All other fields are at the top level (flat format, no envelope wrapper).

Raises ValueError on:
- Empty messages
- Invalid JSON
- Non-object JSON values
- Missing or invalid type field
"""

from __future__ import annotations

import json
from typing import Any


def parse_client_message(raw: str) -> dict[str, Any]:
    """Parse and normalize a client WebSocket message.

    Args:
        raw: Raw message string from WebSocket.

    Returns:
        Normalized message dict with 'type' lowercased.

    Raises:
        ValueError: If message is empty, invalid JSON, or missing type.
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

    msg_type = data.get("type")
    if not msg_type:
        raise ValueError("Missing 'type' in message.")

    data["type"] = str(msg_type).strip().lower()
    return data
