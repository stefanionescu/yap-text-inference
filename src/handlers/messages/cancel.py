"""Cancel message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ...engines import get_chat_engine, get_tool_engine
from ..session_manager import session_manager


async def handle_cancel_message(ws: WebSocket, session_id: str) -> None:
    """Handle 'cancel' message type."""
    if session_id:
        session_manager.cancel_session_requests(session_id)
        req_info = session_manager.cleanup_session_requests(session_id)

        # Abort active chat request
        try:
            if req_info["active"]:
                await (await get_chat_engine()).abort_request(req_info["active"])
        except Exception:
            pass

        # Abort tool request if exists
        try:
            if req_info["tool"]:
                await (await get_tool_engine()).abort_request(req_info["tool"])
        except Exception:
            pass

    await ws.send_text(json.dumps({"type": "done", "cancelled": True}))


