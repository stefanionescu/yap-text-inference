"""Cancel message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ..handlers.session_handler import abort_session_requests


async def handle_cancel_message(ws: WebSocket, session_id: str, request_id: str | None = None) -> None:
    """Handle 'cancel' message type."""
    if session_id:
        await abort_session_requests(session_id, clear_state=False)

    payload = {"type": "done", "cancelled": True}
    if request_id:
        payload["request_id"] = request_id
    await ws.send_text(json.dumps(payload))


