"""Main WebSocket connection handler."""

import contextlib
import json
import logging
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
from ..engines import clear_all_engine_caches_on_disconnect
from ..messages.cancel import handle_cancel_message
from ..messages.chat_prompt import handle_chat_prompt
from ..messages.followup import handle_followup_message
from ..messages.start import handle_start_message
from ..messages.warm_history import handle_warm_history_message
from ..messages.warm_persona import handle_warm_persona_message
from .connection_handler import connection_handler
from .session_handler import abort_session_requests, session_handler
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


_SESSION_MESSAGE_HANDLERS = {
    "followup": handle_followup_message,
    "chat_prompt": handle_chat_prompt,
}

_PAYLOAD_ONLY_HANDLERS = {
    "warm_persona": handle_warm_persona_message,
    "warm_history": handle_warm_history_message,
}


async def _send_error(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    extra: dict | None = None,
) -> None:
    payload = {
        "type": "error",
        "error_code": error_code,
        "message": message,
    }
    if extra:
        payload.update(extra)
    await ws.send_text(json.dumps(payload))


async def _reject_connection(
    ws: WebSocket,
    *,
    error_code: str,
    message: str,
    close_code: int,
    extra: dict | None = None,
) -> None:
    await ws.accept()
    await _send_error(ws, error_code=error_code, message=message, extra=extra)
    await ws.close(code=close_code)


async def _handle_start_command(
    ws: WebSocket,
    msg: dict,
    current_session_id: str | None,
) -> str | None:
    session_id = msg.get("session_id")
    if not session_id:
        await _send_error(
            ws,
            error_code="missing_session_id",
            message="start message must include 'session_id'.",
        )
        return current_session_id

    if current_session_id and session_handler.has_running_task(current_session_id):
        session_handler.cancel_session_requests(current_session_id)

    await handle_start_message(ws, msg, session_id)
    logger.info("WS start scheduled for session_id=%s", session_id)
    return session_id


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers.
    
    Args:
        ws: WebSocket connection
    """
    lifecycle: WebSocketLifecycle | None = None
    
    if not await authenticate_websocket(ws):
        await _reject_connection(
            ws,
            error_code="authentication_failed",
            message=(
                        "Authentication required. Provide valid API key via 'api_key' "
                        "query parameter or 'X-API-Key' header."
                    ),
            close_code=WS_CLOSE_UNAUTHORIZED_CODE,
        )
        return
    
    if not await connection_handler.connect(ws):
        capacity_info = connection_handler.get_capacity_info()
        await _reject_connection(
            ws,
            error_code="server_at_capacity",
            message=(
                "Server is at capacity. "
                f"Active connections: {capacity_info['active']}/{capacity_info['max']}. "
                        "Please try again later."
                    ),
            close_code=WS_CLOSE_BUSY_CODE,
            extra={"capacity": capacity_info},
        )
        return
    
    await ws.accept()
    session_id: str | None = None
    lifecycle = WebSocketLifecycle(ws)
    lifecycle.start()
    
    logger.info(
        "WebSocket connection accepted. Active: %s",
        connection_handler.get_connection_count(),
    )

    try:
        while True:
            raw_msg = await ws.receive_text()
            try:
                msg = _parse_client_message(raw_msg)
            except ValueError as exc:
                await _send_error(
                    ws,
                    error_code="invalid_message",
                    message=str(exc),
                )
                continue

            lifecycle.touch()
            msg_type = msg.get("type")

            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong"}))
                continue

            if msg_type == "pong":
                continue

            if msg_type == "end":
                logger.info("WS recv: end session_id=%s", session_id)
                await ws.send_text(
                    json.dumps(
                        {"type": "connection_closed", "reason": "client_request"}
                    )
                )
                await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
                break

            if msg_type == "start":
                logger.info(
                    "WS recv: start session_id=%s gender=%s len(history)=%s len(user)=%s",
                    msg.get("session_id"),
                    msg.get("assistant_gender"),
                    len(msg.get("history_text", "")),
                    len(msg.get("user_utterance", "")),
                )
                session_id = await _handle_start_command(ws, msg, session_id)
                continue

            if msg_type == "cancel":
                logger.info("WS recv: cancel session_id=%s", session_id)
                await handle_cancel_message(ws, session_id, msg.get("request_id"))
                continue

            handler = _PAYLOAD_ONLY_HANDLERS.get(msg_type)
            if handler:
                logger.info("WS recv: %s", msg_type)
                await handler(ws, msg)
                continue

            session_handler_fn = _SESSION_MESSAGE_HANDLERS.get(msg_type)
            if session_handler_fn:
                logger.info("WS recv: %s session_id=%s", msg_type, session_id)
                await session_handler_fn(ws, msg, session_id)
                continue

            await _send_error(
                ws,
                error_code="unknown_message_type",
                message=f"Message type '{msg_type}' is not supported.",
            )
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("WebSocket error")
        with contextlib.suppress(Exception):
            await _send_error(ws, error_code="internal_error", message=str(exc))
    finally:
        if lifecycle is not None:
            with contextlib.suppress(Exception):
                await lifecycle.stop()
        await _cleanup_session(session_id)
        await connection_handler.disconnect(ws)
        remaining = connection_handler.get_connection_count()
        logger.info("WebSocket connection closed. Active: %s", remaining)
        if remaining == 0:
            with contextlib.suppress(Exception):
                await clear_all_engine_caches_on_disconnect()


async def _cleanup_session(session_id: str | None) -> None:
    """Clean up session resources on disconnect.
    
    Args:
        session_id: Session identifier to clean up
    """
    await abort_session_requests(session_id, clear_state=True)
