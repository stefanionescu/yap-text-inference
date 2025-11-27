"""Primary WebSocket connection handler orchestration."""

from __future__ import annotations

import contextlib
import json
import logging
import math
from typing import Any
from collections.abc import Callable

from fastapi import WebSocket, WebSocketDisconnect

from ...auth import authenticate_websocket
from ...config import (
    WS_CANCEL_WINDOW_SECONDS,
    WS_MAX_CANCELS_PER_WINDOW,
    WS_MAX_MESSAGES_PER_WINDOW,
    WS_MESSAGE_WINDOW_SECONDS,
)
from ...config.websocket import (
    WS_CLOSE_BUSY_CODE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
    WS_CLOSE_UNAUTHORIZED_CODE,
)
from ...engines import clear_all_engine_caches_on_disconnect
from ...messages.cancel import handle_cancel_message
from ...messages.chat_prompt import handle_chat_prompt
from ...messages.followup import handle_followup_message
from ...messages.start import handle_start_message
from ...messages.warm.warm_history import handle_warm_history_message
from ...messages.warm.warm_persona import handle_warm_persona_message
from ...utils import RateLimitError, SlidingWindowRateLimiter
from ..connection_handler import connection_handler
from ..session import abort_session_requests, session_handler
from .lifecycle import WebSocketLifecycle
from .errors import reject_connection, send_error
from .parser import parse_client_message

logger = logging.getLogger(__name__)

SessionHandlerFn = Callable[[WebSocket, dict[str, Any], str | None], Any]

_SESSION_MESSAGE_HANDLERS: dict[str, SessionHandlerFn] = {
    "followup": handle_followup_message,
    "chat_prompt": handle_chat_prompt,
}

_PAYLOAD_ONLY_HANDLERS: dict[str, Callable[[WebSocket, dict[str, Any]], Any]] = {
    "warm_persona": handle_warm_persona_message,
    "warm_history": handle_warm_history_message,
}


async def _prepare_connection(ws: WebSocket) -> bool:
    if not await authenticate_websocket(ws):
        await reject_connection(
            ws,
            error_code="authentication_failed",
            message=(
                "Authentication required. Provide valid API key via 'api_key' "
                "query parameter or 'X-API-Key' header."
            ),
            close_code=WS_CLOSE_UNAUTHORIZED_CODE,
        )
        return False

    if not await connection_handler.connect(ws):
        capacity_info = connection_handler.get_capacity_info()
        await reject_connection(
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
        return False

    await ws.accept()
    return True


def _select_rate_limiter(
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> tuple[SlidingWindowRateLimiter | None, str]:
    if msg_type == "cancel":
        return cancel_limiter, "cancel"
    if msg_type in {"ping", "pong", "end"}:
        return None, ""
    return message_limiter, "message"


async def _consume_limiter(
    ws: WebSocket,
    limiter: SlidingWindowRateLimiter,
    label: str,
) -> bool:
    try:
        limiter.consume()
    except RateLimitError as err:
        retry_in = int(max(1, math.ceil(err.retry_in))) if err.retry_in > 0 else 1
        limit_desc = limiter.limit
        window_desc = int(limiter.window_seconds)
        message = (
            f"{label} rate limit: at most {limit_desc} per {window_desc} seconds; "
            f"retry in {retry_in} seconds"
        )
        await send_error(
            ws,
            error_code=f"{label}_rate_limited",
            message=message,
            extra={"retry_in": retry_in},
        )
        return False
    return True


async def _handle_control_message(
    ws: WebSocket,
    msg_type: str,
    session_id: str | None,
) -> bool:
    if msg_type == "ping":
        await ws.send_text(json.dumps({"type": "pong"}))
        return False
    if msg_type == "pong":
        return False
    if msg_type == "end":
        logger.info("WS recv: end session_id=%s", session_id)
        await ws.send_text(
            json.dumps({"type": "connection_closed", "reason": "client_request"})
        )
        await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
        return True
    return False


async def _handle_start_command(
    ws: WebSocket,
    msg: dict[str, Any],
    current_session_id: str | None,
) -> str | None:
    session_id = msg.get("session_id")
    if not session_id:
        await send_error(
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


async def _cleanup_session(session_id: str | None) -> None:
    """Clean up session resources on disconnect."""

    await abort_session_requests(session_id, clear_state=True)


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers."""

    lifecycle: WebSocketLifecycle | None = None
    admitted = False

    if not await _prepare_connection(ws):
        return

    admitted = True
    session_id: str | None = None
    message_limiter = SlidingWindowRateLimiter(
        limit=WS_MAX_MESSAGES_PER_WINDOW,
        window_seconds=WS_MESSAGE_WINDOW_SECONDS,
    )
    cancel_limiter = SlidingWindowRateLimiter(
        limit=WS_MAX_CANCELS_PER_WINDOW,
        window_seconds=WS_CANCEL_WINDOW_SECONDS,
    )
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
                msg = parse_client_message(raw_msg)
            except ValueError as exc:
                await send_error(
                    ws,
                    error_code="invalid_message",
                    message=str(exc),
                )
                continue

            lifecycle.touch()
            msg_type = msg.get("type")

            limiter, label = _select_rate_limiter(msg_type, message_limiter, cancel_limiter)
            if limiter and not await _consume_limiter(ws, limiter, label):
                continue

            if await _handle_control_message(ws, msg_type, session_id):
                break

            if msg_type == "start":
                logger.info(
                    "WS recv: start session_id=%s gender=%s len(history)=%s len(user)=%s",
                    msg.get("session_id"),
                    msg.get("gender"),
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

            await send_error(
                ws,
                error_code="unknown_message_type",
                message=f"Message type '{msg_type}' is not supported.",
            )
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.exception("WebSocket error")
        with contextlib.suppress(Exception):
            await send_error(ws, error_code="internal_error", message=str(exc))
    finally:
        if lifecycle is not None:
            with contextlib.suppress(Exception):
                await lifecycle.stop()
        await _cleanup_session(session_id)
        if admitted:
            await connection_handler.disconnect(ws)
            remaining = connection_handler.get_connection_count()
            logger.info("WebSocket connection closed. Active: %s", remaining)
            if remaining == 0:
                with contextlib.suppress(Exception):
                    await clear_all_engine_caches_on_disconnect()


