"""Main WebSocket connection handler."""

import contextlib
import json
import logging
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect

from ..auth import authenticate_websocket
from ..config import DEPLOY_CHAT, DEPLOY_TOOL
from ..config.websocket import (
    WS_CLOSE_BUSY_CODE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
    WS_CLOSE_UNAUTHORIZED_CODE,
    WS_CANCEL_SENTINEL,
    WS_END_SENTINEL,
)
from ..engines import get_chat_engine, get_tool_engine, clear_all_engine_caches_on_disconnect
from ..messages.cancel import handle_cancel_message
from ..messages.chat_prompt import handle_chat_prompt
from ..messages.followup import handle_followup_message
from ..messages.start import handle_start_message
from ..messages.warm_history import handle_warm_history_message
from ..messages.warm_persona import handle_warm_persona_message
from .connection_handler import connection_handler
from .session_handler import session_handler
from .ws_lifecycle import WebSocketLifecycle

logger = logging.getLogger(__name__)


def _parse_client_message(raw: str) -> dict:
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


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers.
    
    Args:
        ws: WebSocket connection
    """
    # Check API key authentication first
    is_authenticated = await authenticate_websocket(ws)
    lifecycle: Optional[WebSocketLifecycle] = None
    
    if not is_authenticated:
        # Authentication failed - send error and close
        await ws.accept()  # Need to accept to send error message
        await ws.send_text(json.dumps({
            "type": "error",
            "error_code": "authentication_failed",
            "message": "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header.",
        }))
        await ws.close(code=WS_CLOSE_UNAUTHORIZED_CODE)
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
        await ws.close(code=WS_CLOSE_BUSY_CODE)
        return
    
    # Connection accepted - proceed normally
    await ws.accept()
    session_id: Optional[str] = None
    lifecycle = WebSocketLifecycle(ws)
    lifecycle.start()
    
    logger.info(f"WebSocket connection accepted. Active: {connection_handler.get_connection_count()}")

    try:
        while True:
            raw_msg = await ws.receive_text()
            try:
                msg = _parse_client_message(raw_msg)
            except ValueError as exc:
                await ws.send_text(
                    json.dumps(
                        {
                            "type": "error",
                            "error_code": "invalid_message",
                            "message": str(exc),
                        }
                    )
                )
                continue
            lifecycle.touch()

            msg_type = (msg.get("type") or "").strip().lower()

            if not msg_type:
                await ws.send_text(json.dumps({
                    "type": "error",
                    "error_code": "invalid_message",
                    "message": "Missing 'type' field in message."
                }))
                continue

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "pong":
                continue

            if msg_type == "end":
                logger.info(f"WS recv: end session_id={session_id}")
                await ws.send_text(json.dumps({"type": "connection_closed", "reason": "client_request"}))
                await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
                break

            if msg_type == "start":
                logger.info(f"WS recv: start session_id={msg.get('session_id')} gender={msg.get('assistant_gender')} len(history)={len(msg.get('history_text',''))} len(user)={len(msg.get('user_utterance',''))}")
                # Cancel previous session if exists
                if session_id and session_id in session_handler.session_tasks:
                    session_handler.cancel_session_requests(session_id)

                session_id = msg["session_id"]
                await handle_start_message(ws, msg, session_id)
                logger.info(f"WS start scheduled for session_id={session_id}")

            elif msg_type == "cancel":
                logger.info(f"WS recv: cancel session_id={session_id}")
                await handle_cancel_message(ws, session_id, msg.get("request_id"))

            elif msg_type == "warm_persona":
                logger.info("WS recv: warm_persona")
                await handle_warm_persona_message(ws, msg)

            elif msg_type == "warm_history":
                logger.info("WS recv: warm_history")
                await handle_warm_history_message(ws, msg)

            elif msg_type == "followup":
                logger.info("WS recv: followup")
                await handle_followup_message(ws, msg, session_id)

            elif msg_type == "chat_prompt":
                logger.info("WS recv: chat_prompt")
                await handle_chat_prompt(ws, msg, session_id)

            else:
                await ws.send_text(json.dumps({
                    "type": "error", 
                    "message": "unknown msg type"
                }))

    except WebSocketDisconnect:
        pass
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
        if lifecycle is not None:
            with contextlib.suppress(Exception):
                await lifecycle.stop()
        await _cleanup_session(session_id)
        # Always remove connection from manager when done
        await connection_handler.disconnect(ws)
        remaining = connection_handler.get_connection_count()
        logger.info(f"WebSocket connection closed. Active: {remaining}")
        if remaining == 0:
            with contextlib.suppress(Exception):
                await clear_all_engine_caches_on_disconnect()


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
    
    # Abort active chat request (only if chat is deployed)
    if DEPLOY_CHAT:
    try:
        if req_info["active"]:
            await (await get_chat_engine()).abort_request(req_info["active"])
    except Exception:
        pass
    
    # Abort tool request if exists (only if tool is deployed)
    if DEPLOY_TOOL:
    try:
        if req_info["tool"]:
            await (await get_tool_engine()).abort_request(req_info["tool"])
    except Exception:
        pass

    # Drop session state after cleanup
    session_handler.clear_session_state(session_id)
