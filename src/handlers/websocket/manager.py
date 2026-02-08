"""Primary WebSocket connection handler orchestration.

This module contains the main WebSocket connection handler that serves as
the entry point for all client connections. It orchestrates connection setup,
message routing, rate limiting, and cleanup on disconnect.

Message Types:
    start       - Initialize session with persona and start generation
    cancel      - Abort active generation request
    followup    - Continue conversation (skip tool routing)
    ping/pong   - Keep-alive heartbeat
    end         - Client-initiated disconnect
"""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any
from collections.abc import Callable

from fastapi import WebSocket, WebSocketDisconnect

from ..instances import connections
from .helpers import safe_send_envelope
from .auth import authenticate_websocket
from .parser import parse_client_message
from .lifecycle import WebSocketLifecycle
from ..limits import SlidingWindowRateLimiter
from .errors import send_error, reject_connection
from ...messages.start import handle_start_message
from ...messages.cancel import handle_cancel_message
from ...messages.followup import handle_followup_message
from .limits import consume_limiter, select_rate_limiter
from ..session import session_handler, abort_session_requests
from ...engines import reset_engine_caches, clear_caches_on_disconnect
from ...logging import log_context, set_log_context, reset_log_context
from ...config import (
    WS_CANCEL_WINDOW_SECONDS,
    WS_MAX_CANCELS_PER_WINDOW,
    WS_MESSAGE_WINDOW_SECONDS,
    WS_MAX_MESSAGES_PER_WINDOW,
    CACHE_RESET_MIN_SESSION_SECONDS,
)
from ...config.websocket import (
    WS_ERROR_INTERNAL,
    WS_CLOSE_BUSY_CODE,
    WS_WATCHDOG_TICK_S,
    WS_ERROR_AUTH_FAILED,
    WS_ERROR_SERVER_BUSY,
    WS_ERROR_INVALID_MESSAGE,
    WS_ERROR_INVALID_PAYLOAD,
    WS_CLOSE_UNAUTHORIZED_CODE,
    WS_CLOSE_CLIENT_REQUEST_CODE,
)

logger = logging.getLogger(__name__)

# Type alias for session-aware message handlers
SessionHandlerFn = Callable[[WebSocket, dict[str, Any], str, str], Any]

# Handlers that receive (ws, payload, session_id, request_id)
_SESSION_MESSAGE_HANDLERS: dict[str, SessionHandlerFn] = {
    "followup": handle_followup_message,
}


async def _prepare_connection(ws: WebSocket) -> bool:
    """Authenticate and admit a WebSocket connection.

    Performs two checks:
    1. API key authentication (rejects with 4001 if invalid)
    2. Capacity check (rejects with 4003 if at max connections)

    Args:
        ws: The incoming WebSocket connection.

    Returns:
        True if connection was accepted, False if rejected.
    """
    if not await authenticate_websocket(ws):
        await reject_connection(
            ws,
            error_code=WS_ERROR_AUTH_FAILED,
            message=(
                "Authentication required. Provide valid API key via 'api_key' query parameter or 'X-API-Key' header."
            ),
            close_code=WS_CLOSE_UNAUTHORIZED_CODE,
        )
        return False

    if not await connections.connect(ws):
        await reject_connection(
            ws,
            error_code=WS_ERROR_SERVER_BUSY,
            message="Server cannot accept new connections. Please try again later.",
            close_code=WS_CLOSE_BUSY_CODE,
        )
        return False

    try:
        await ws.accept()
    except Exception:  # noqa: BLE001 - propagate after releasing slot
        with contextlib.suppress(Exception):
            await connections.disconnect(ws)
        raise
    return True


async def _handle_control_message(
    ws: WebSocket,
    msg_type: str,
    session_id: str,
    request_id: str,
) -> bool:
    """Process ping/pong/end messages; return True if connection should close."""
    if msg_type == "ping":
        await safe_send_envelope(
            ws,
            msg_type="pong",
            session_id=session_id,
            request_id=request_id,
            payload={},
        )
        return False
    if msg_type == "pong":
        return False
    if msg_type == "end":
        logger.info("WS recv: end session_id=%s", session_id)
        await safe_send_envelope(
            ws,
            msg_type="session_end",
            session_id=session_id,
            request_id=request_id,
            payload={"reason": "client_request"},
        )
        with contextlib.suppress(Exception):
            await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
        return True
    return False


async def _handle_start_command(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
    current_session_id: str | None,
) -> str | None:
    if current_session_id and session_handler.has_running_task(current_session_id):
        await abort_session_requests(current_session_id, clear_state=False)

    await handle_start_message(ws, payload, session_id, request_id)
    logger.info("WS start scheduled for session_id=%s request_id=%s", session_id, request_id)
    return session_id


async def _cleanup_session(session_id: str | None) -> float:
    """Clean up session resources on disconnect and return duration."""

    duration = 0.0
    if session_id:
        duration = session_handler.get_session_duration(session_id)
    await abort_session_requests(session_id, clear_state=True)
    return duration


def _create_rate_limiters() -> tuple[SlidingWindowRateLimiter, SlidingWindowRateLimiter]:
    """Initialize per-connection rate limiters."""
    message_limiter = SlidingWindowRateLimiter(
        limit=WS_MAX_MESSAGES_PER_WINDOW,
        window_seconds=WS_MESSAGE_WINDOW_SECONDS,
    )
    cancel_limiter = SlidingWindowRateLimiter(
        limit=WS_MAX_CANCELS_PER_WINDOW,
        window_seconds=WS_CANCEL_WINDOW_SECONDS,
    )
    return message_limiter, cancel_limiter


async def _run_message_loop(  # noqa: PLR0915
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> str | None:
    """Receive, validate, and dispatch client messages."""
    session_id: str | None = None

    while True:
        try:
            raw_msg = await asyncio.wait_for(
                ws.receive_text(),
                timeout=WS_WATCHDOG_TICK_S * 2,
            )
        except asyncio.TimeoutError:
            if lifecycle.should_close():
                break
            continue

        try:
            msg = parse_client_message(raw_msg)
        except ValueError as exc:
            await send_error(
                ws,
                error_code=WS_ERROR_INVALID_MESSAGE,
                message=str(exc),
                reason_code="invalid_message",
            )
            continue

        lifecycle.touch()
        msg_type = msg.get("type")
        if not isinstance(msg_type, str):
            await send_error(
                ws,
                error_code=WS_ERROR_INVALID_MESSAGE,
                message="message missing type field",
                reason_code="invalid_message_type",
            )
            continue

        raw_session_id = msg.get("session_id")
        raw_request_id = msg.get("request_id")
        msg_session_id = raw_session_id if isinstance(raw_session_id, str) else ""
        msg_request_id = raw_request_id if isinstance(raw_request_id, str) else ""
        payload = msg.get("payload") or {}

        with log_context(session_id=msg_session_id, request_id=msg_request_id):
            limiter, label = select_rate_limiter(msg_type, message_limiter, cancel_limiter)
            if limiter and not await consume_limiter(
                ws,
                limiter,
                label,
                session_id=msg_session_id,
                request_id=msg_request_id,
            ):
                continue

            if msg_type in {"ping", "pong", "end"}:
                if await _handle_control_message(ws, msg_type, msg_session_id, msg_request_id):
                    break
                continue

            if msg_type == "start":
                logger.info(
                    "WS recv: start session_id=%s gender=%s len(history)=%s len(user)=%s",
                    msg_session_id,
                    payload.get("gender"),
                    len(payload.get("history", [])),
                    len(payload.get("user_utterance", "")),
                )
                session_id = await _handle_start_command(
                    ws,
                    payload,
                    msg_session_id,
                    msg_request_id,
                    session_id,
                )
                continue

            if session_id and msg_session_id != session_id:
                await send_error(
                    ws,
                    session_id=msg_session_id,
                    request_id=msg_request_id,
                    error_code=WS_ERROR_INVALID_PAYLOAD,
                    message="session_id does not match active session.",
                    reason_code="invalid_session_id",
                )
                continue
            if not session_id:
                await send_error(
                    ws,
                    session_id=msg_session_id,
                    request_id=msg_request_id,
                    error_code=WS_ERROR_INVALID_MESSAGE,
                    message="no active session; send 'start' first.",
                    reason_code="no_active_session",
                )
                continue

            if msg_type == "cancel":
                logger.info("WS recv: cancel session_id=%s request_id=%s", session_id, msg_request_id)
                await handle_cancel_message(ws, session_id, msg_request_id)
                continue

            session_handler_fn = _SESSION_MESSAGE_HANDLERS.get(msg_type)
            if session_handler_fn:
                logger.info("WS recv: %s session_id=%s", msg_type, session_id)
                await session_handler_fn(ws, payload, session_id, msg_request_id)
                continue

            await send_error(
                ws,
                session_id=msg_session_id,
                request_id=msg_request_id,
                error_code=WS_ERROR_INVALID_MESSAGE,
                message=f"Message type '{msg_type}' is not supported.",
                reason_code="unknown_message_type",
            )

    return session_id


async def _finalize_connection(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle | None,
    session_id: str | None,
    admitted: bool,
) -> None:
    """Handle teardown actions after the connection loop exits."""
    if lifecycle is not None:
        with contextlib.suppress(Exception):
            await lifecycle.stop()

    session_duration = 0.0
    try:
        session_duration = await _cleanup_session(session_id)
    except Exception:  # noqa: BLE001
        logger.exception("WebSocket cleanup failed")

    if not admitted:
        return

    with contextlib.suppress(Exception):
        await connections.disconnect(ws)
    remaining = connections.get_connection_count()
    logger.info("WebSocket connection closed. Active: %s", remaining)
    should_reset = session_id is not None and session_duration >= CACHE_RESET_MIN_SESSION_SECONDS
    if should_reset:
        with contextlib.suppress(Exception):
            triggered = await reset_engine_caches("long_session", force=True)
            if triggered:
                logger.info(
                    "cache reset after long session_id=%s duration=%.1fs",
                    session_id,
                    session_duration,
                )
    if remaining == 0:
        with contextlib.suppress(Exception):
            await clear_caches_on_disconnect()


async def handle_websocket_connection(ws: WebSocket) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers.

    This is the main entry point for WebSocket connections. It:
    1. Authenticates and admits the connection
    2. Starts idle timeout watchdog
    3. Loops receiving messages and dispatching to handlers
    4. Cleans up on disconnect (session state, engine caches, connection slot)

    Args:
        ws: The incoming WebSocket connection from FastAPI.
    """

    client = ws.client
    client_id = f"{client.host}:{client.port}" if client else "unknown"
    tokens = set_log_context(client_id=client_id)
    try:
        lifecycle: WebSocketLifecycle | None = None
        admitted = False

        if not await _prepare_connection(ws):
            return

        admitted = True
        session_id: str | None = None
        message_limiter, cancel_limiter = _create_rate_limiters()
        lifecycle = WebSocketLifecycle(ws)
        lifecycle.start()

        logger.info(
            "WebSocket connection accepted. Active: %s",
            connections.get_connection_count(),
        )

        try:
            session_id = await _run_message_loop(ws, lifecycle, message_limiter, cancel_limiter)
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001
            logger.exception("WebSocket error")
            with contextlib.suppress(Exception):
                await send_error(
                    ws,
                    session_id=session_id,
                    request_id=None,
                    error_code=WS_ERROR_INTERNAL,
                    message=str(exc),
                    reason_code="internal_exception",
                )
        finally:
            await _finalize_connection(ws, lifecycle, session_id, admitted)
    finally:
        reset_log_context(tokens)
