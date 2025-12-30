"""Cancel message handler for aborting in-flight requests.

This module handles the 'cancel' WebSocket message type, which allows
clients to abort ongoing generation requests. The handler:

1. Aborts any active requests tracked by the session
2. Cancels the associated asyncio.Task
3. Best-effort aborts the engine request
4. Sends a 'done' response with cancelled=True

Cancellation is cooperative - the generation stream checks for
cancellation periodically and terminates gracefully.
"""

import json
from fastapi import WebSocket

from ..handlers.session import abort_session_requests
from ..handlers.websocket.helpers import safe_send_text


async def handle_cancel_message(ws: WebSocket, session_id: str, request_id: str | None = None) -> None:
    """Handle 'cancel' message type by aborting active requests.
    
    Args:
        ws: WebSocket connection for response.
        session_id: Session to cancel requests for.
        request_id: Optional specific request ID (included in response).
    """
    if session_id:
        await abort_session_requests(session_id, clear_state=False)

    payload = {"type": "done", "cancelled": True}
    if request_id:
        payload["request_id"] = request_id
    await safe_send_text(ws, json.dumps(payload))

