"""Main WebSocket connection handler."""

import json
import logging
from typing import Optional
from fastapi import WebSocket, WebSocketDisconnect

from ..engines import get_chat_engine, get_tool_engine, clear_all_engine_caches_on_disconnect
from ..handlers.session_handler import session_handler
from ..handlers.connection_handler import connection_handler
from ..auth import authenticate_websocket
from ..messages.start import handle_start_message
from ..messages.cancel import handle_cancel_message
from ..messages.warm_persona import handle_warm_persona_message
from ..messages.warm_history import handle_warm_history_message
from ..messages.followup import handle_followup_message
from ..messages.chat_prompt import handle_chat_prompt

logger = logging.getLogger(__name__)


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers.
    
    Args:
        ws: WebSocket connection
    """
    # Check API key authentication first
    is_authenticated = await authenticate_websocket(ws)
    
    if not is_authenticated:
        # Authentication failed - send error and close
        await ws.accept()  # Need to accept to send error message
        await ws.send_text(json.dumps({
            "type": "error",
            "error_code": "authentication_failed",
            "message": "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header.",
        }))
        await ws.close(code=1008)  # 1008 = Policy Violation
        return
    
    # Check connection limit after authentication
    can_connect = await connection_handler.connect(ws)
    
    if not can_connect:
        # Server at capacity - send error and close connection
        capacity_info = connection_handler.get_capacity_info()
        await ws.accept()  # Need to accept to send error message
        await ws.send_text(json.dumps({
            "type": "error",
            "error_code": "server_at_capacity", 
            "message": f"Server is at capacity. Active connections: {capacity_info['active']}/{capacity_info['max']}. Please try again later.",
            "capacity": capacity_info
        }))
        await ws.close(code=1013)  # 1013 = Try Again Later
        return
    
    # Connection accepted - proceed normally
    await ws.accept()
    session_id: Optional[str] = None
    
    logger.info(f"WebSocket connection accepted. Active: {connection_handler.get_connection_count()}")

    try:
        while True:
            msg = json.loads(await ws.receive_text())

            if msg["type"] == "start":
                logger.info(f"WS recv: start session_id={msg.get('session_id')} gender={msg.get('assistant_gender')} len(history)={len(msg.get('history_text',''))} len(user)={len(msg.get('user_utterance',''))}")
                # Cancel previous session if exists
                if session_id and session_id in session_handler.session_tasks:
                    session_handler.cancel_session_requests(session_id)

                session_id = msg["session_id"]
                await handle_start_message(ws, msg, session_id)
                logger.info(f"WS start scheduled for session_id={session_id}")

            elif msg["type"] == "cancel":
                logger.info(f"WS recv: cancel session_id={session_id}")
                await handle_cancel_message(ws, session_id)

            elif msg["type"] == "warm_persona":
                logger.info("WS recv: warm_persona")
                await handle_warm_persona_message(ws, msg)

            elif msg["type"] == "warm_history":
                logger.info("WS recv: warm_history")
                await handle_warm_history_message(ws, msg)


            elif msg["type"] == "followup":
                logger.info("WS recv: followup")
                await handle_followup_message(ws, msg, session_id)

            elif msg["type"] == "chat_prompt":
                logger.info("WS recv: chat_prompt")
                await handle_chat_prompt(ws, msg, session_id)

            else:
                await ws.send_text(json.dumps({
                    "type": "error", 
                    "message": "unknown msg type"
                }))

    except WebSocketDisconnect:
        await _cleanup_session(session_id)
    except Exception as e:
        logger.exception("WebSocket error")
        try:
            await ws.send_text(json.dumps({
                "type": "error", 
                "message": str(e)
            }))
        except Exception:
            # Connection might already be closed
            pass
    finally:
        # Always remove connection from manager when done
        await connection_handler.disconnect(ws)
        remaining = connection_handler.get_connection_count()
        logger.info(f"WebSocket connection closed. Active: {remaining}")
        if remaining == 0:
            try:
                await clear_all_engine_caches_on_disconnect()
            except Exception:
                pass


async def _cleanup_session(session_id: Optional[str]) -> None:
    """Clean up session resources on disconnect.
    
    Args:
        session_id: Session identifier to clean up
    """
    if not session_id:
        return
        
    # Cancel requests and get request IDs for cleanup
    session_handler.cancel_session_requests(session_id)
    req_info = session_handler.cleanup_session_requests(session_id)
    
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

    # Drop session state after cleanup
    session_handler.clear_session_state(session_id)
