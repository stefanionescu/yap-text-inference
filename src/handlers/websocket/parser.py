"""Client payload parsing for the WebSocket handler."""

from __future__ import annotations

import json
from typing import Any

from ...config.websocket import WS_CANCEL_SENTINEL, WS_END_SENTINEL


def parse_client_message(raw: str) -> dict[str, Any]:
    """Normalize client message types to align with Yap TTS server contract."""

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


