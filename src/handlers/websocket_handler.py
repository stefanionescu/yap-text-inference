"""Main WebSocket connection handler."""

import json
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

from ..engines import get_chat_engine, get_tool_engine
from ..handlers.session_manager import session_manager
from ..handlers.message_handlers import (
    handle_start_message,
    handle_cancel_message,
    handle_warm_persona_message,
    handle_warm_history_message,
    handle_set_persona_message,
)


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers.
    
    Args:
        ws: WebSocket connection
    """
    await ws.accept()
    session_id: Optional[str] = None

    try:
        while True:
            msg = json.loads(await ws.receive_text())

            if msg["type"] == "start":
                # Cancel previous session if exists
                if session_id and session_id in session_manager.session_tasks:
                    session_manager.cancel_session_requests(session_id)

                session_id = msg["session_id"]
                await handle_start_message(ws, msg, session_id)

            elif msg["type"] == "cancel":
                await handle_cancel_message(ws, session_id)

            elif msg["type"] == "warm_persona":
                await handle_warm_persona_message(ws, msg)

            elif msg["type"] == "warm_history":
                await handle_warm_history_message(ws, msg)

            elif msg["type"] == "set_persona":
                await handle_set_persona_message(ws, msg, session_id)

            else:
                await ws.send_text(json.dumps({
                    "type": "error", 
                    "message": "unknown msg type"
                }))

    except WebSocketDisconnect:
        await _cleanup_session(session_id)
    except Exception as e:
        await ws.send_text(json.dumps({
            "type": "error", 
            "message": str(e)
        }))


async def _cleanup_session(session_id: Optional[str]) -> None:
    """Clean up session resources on disconnect.
    
    Args:
        session_id: Session identifier to clean up
    """
    if not session_id:
        return
        
    # Cancel requests and get request IDs for cleanup
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
