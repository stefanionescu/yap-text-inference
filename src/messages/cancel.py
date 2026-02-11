"""Cancel message handler for aborting in-flight requests.

This module handles the 'cancel' WebSocket message type, which allows
clients to abort ongoing generation requests. The handler:

1. Aborts any active requests tracked by the session
2. Cancels the associated asyncio.Task
3. Best-effort aborts the engine request
4. Sends a 'cancelled' acknowledgement

Cancellation is cooperative - the generation stream checks for
cancellation periodically and terminates gracefully.
"""

from fastapi import WebSocket

from ..handlers.instances import session_handler
from ..handlers.websocket.helpers import safe_send_envelope


async def handle_cancel_message(ws: WebSocket, session_id: str, request_id: str) -> None:
    """Handle 'cancel' message type by aborting active requests.

    Args:
        ws: WebSocket connection for response.
        session_id: Session to cancel requests for.
        request_id: Request ID to cancel/acknowledge.
    """
    if session_id:
        await session_handler.abort_session_requests(session_id, clear_state=False)

    await safe_send_envelope(
        ws,
        msg_type="cancelled",
        session_id=session_id,
        request_id=request_id,
        payload={"reason": "client_request"},
    )
