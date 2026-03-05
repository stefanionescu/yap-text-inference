"""Cancel message handler for aborting in-flight requests.

This module handles the 'cancel' WebSocket message type, which allows
clients to abort ongoing generation requests. The handler:

1. Aborts any active requests tracked by the session
2. Cancels the associated asyncio.Task
3. Best-effort aborts the engine request
4. Sends a 'cancelled' confirmation
"""

from fastapi import WebSocket
from src.state.session import SessionState
from ..handlers.websocket.helpers import safe_send_flat
from src.handlers.session.manager import SessionHandler


async def handle_cancel_message(
    ws: WebSocket,
    state: SessionState,
    *,
    session_handler: SessionHandler,
) -> None:
    """Handle 'cancel' message type by aborting active requests."""
    await session_handler.abort_session_requests(state)
    await safe_send_flat(ws, "cancelled")
