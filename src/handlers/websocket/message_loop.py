"""WebSocket message loop and dispatch helpers."""

from __future__ import annotations

import logging
import contextlib
from typing import Any, cast
from collections.abc import Callable

from fastapi import WebSocket

from src.runtime.dependencies import RuntimeDeps
from src.handlers.session.manager import SessionHandler

from .errors import send_error
from ...logging import log_context
from .helpers import safe_send_envelope
from .parser import parse_client_message
from .lifecycle import WebSocketLifecycle
from ..limits import SlidingWindowRateLimiter
from ...telemetry.instruments import get_metrics
from .disconnects import is_expected_ws_disconnect
from ...messages.cancel import handle_cancel_message
from ...messages.message import handle_message_message
from ...messages.followup import handle_followup_message
from .limits import consume_limiter, select_rate_limiter
from ...messages.start.handler import handle_start_message
from ...config.websocket import WS_ERROR_INVALID_MESSAGE, WS_ERROR_INVALID_PAYLOAD, WS_CLOSE_CLIENT_REQUEST_CODE

logger = logging.getLogger(__name__)

SessionMessageHandlerFn = Callable[..., Any]

_SESSION_MESSAGE_HANDLERS: dict[str, SessionMessageHandlerFn] = {
    "followup": handle_followup_message,
}


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


async def _parse_incoming(ws: WebSocket, raw_msg: str) -> tuple[str, str, str, dict[str, Any]] | None:
    """Parse raw text into (msg_type, session_id, request_id, payload) or None on error."""
    try:
        msg = parse_client_message(raw_msg)
    except ValueError as exc:
        await send_error(ws, error_code=WS_ERROR_INVALID_MESSAGE, message=str(exc), reason_code="invalid_message")
        return None
    return msg["type"], msg["session_id"], msg["request_id"], msg["payload"]


async def _apply_rate_limit(
    ws: WebSocket,
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    *,
    session_id: str,
    request_id: str,
) -> bool:
    limiter, label = select_rate_limiter(msg_type, message_limiter, cancel_limiter)
    if limiter is None:
        return True
    return await consume_limiter(
        ws,
        limiter,
        label,
        session_id=session_id,
        request_id=request_id,
    )


async def _ensure_active_session(
    ws: WebSocket,
    active_session_id: str | None,
    msg_session_id: str,
    msg_request_id: str,
) -> bool:
    if active_session_id and msg_session_id != active_session_id:
        await send_error(
            ws,
            session_id=msg_session_id,
            request_id=msg_request_id,
            error_code=WS_ERROR_INVALID_PAYLOAD,
            message="session_id does not match active session.",
            reason_code="invalid_session_id",
        )
        return False
    if active_session_id:
        return True
    await send_error(
        ws,
        session_id=msg_session_id,
        request_id=msg_request_id,
        error_code=WS_ERROR_INVALID_MESSAGE,
        message="no active session; send 'start' first.",
        reason_code="no_active_session",
    )
    return False


async def _handle_start_command(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
    active_session_id: str | None,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> str | None:
    if active_session_id is not None:
        await send_error(
            ws,
            session_id=session_id,
            request_id=request_id,
            error_code=WS_ERROR_INVALID_MESSAGE,
            message="start may only be sent once per connection; use 'message' for subsequent turns.",
            reason_code="duplicate_start",
        )
        return active_session_id
    get_metrics().requests_total.add(1, {"status": "started"})
    logger.info(
        "WS recv: start session_id=%s request_id=%s gender=%s len(history)=%s len(user)=%s",
        session_id,
        request_id,
        payload.get("gender"),
        len(payload.get("history", [])),
        len(payload.get("user_utterance", "")),
    )
    await handle_start_message(
        ws,
        payload,
        session_id,
        request_id,
        session_handler=session_handler,
        runtime_deps=runtime_deps,
    )
    return session_id


async def _handle_message_command(
    ws: WebSocket,
    payload: dict[str, Any],
    session_id: str,
    request_id: str,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    if session_handler.has_running_task(session_id):
        await session_handler.abort_session_requests(session_id, clear_state=False)
    await handle_message_message(
        ws,
        payload,
        session_id,
        request_id,
        session_handler=session_handler,
        runtime_deps=runtime_deps,
    )


async def _dispatch_session_message(
    ws: WebSocket,
    *,
    msg_type: str,
    payload: dict[str, Any],
    msg_session_id: str,
    msg_request_id: str,
    active_session_id: str | None,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> str | None:
    if msg_type == "start":
        return await _handle_start_command(
            ws,
            payload,
            msg_session_id,
            msg_request_id,
            active_session_id,
            session_handler=session_handler,
            runtime_deps=runtime_deps,
        )
    if not await _ensure_active_session(ws, active_session_id, msg_session_id, msg_request_id):
        return active_session_id
    active_session_id = cast(str, active_session_id)
    if msg_type == "message":
        await _handle_message_command(
            ws,
            payload,
            active_session_id,
            msg_request_id,
            session_handler=session_handler,
            runtime_deps=runtime_deps,
        )
        return active_session_id
    if msg_type == "cancel":
        get_metrics().cancellation_total.add(1)
        logger.info("WS recv: cancel session_id=%s request_id=%s", active_session_id, msg_request_id)
        await handle_cancel_message(ws, active_session_id, msg_request_id, session_handler=session_handler)
        return active_session_id
    session_handler_fn = _SESSION_MESSAGE_HANDLERS.get(msg_type)
    if session_handler_fn:
        logger.info("WS recv: %s session_id=%s", msg_type, active_session_id)
        await session_handler_fn(
            ws,
            payload,
            active_session_id,
            msg_request_id,
            session_handler=session_handler,
            runtime_deps=runtime_deps,
        )
    else:
        await send_error(
            ws,
            session_id=msg_session_id,
            request_id=msg_request_id,
            error_code=WS_ERROR_INVALID_MESSAGE,
            message=f"Message type '{msg_type}' is not supported.",
            reason_code="unknown_message_type",
        )
    return active_session_id


async def run_message_loop(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    runtime_deps: RuntimeDeps,
) -> str | None:
    """Receive, validate, and dispatch client messages."""
    session_id: str | None = None
    session_handler = runtime_deps.session_handler

    while True:
        try:
            raw_msg = await ws.receive_text()
        except Exception as exc:  # noqa: BLE001 - narrowed by classification helper
            if lifecycle.idle_timed_out() or is_expected_ws_disconnect(exc):
                break
            raise

        result = await _parse_incoming(ws, raw_msg)
        if result is None:
            continue

        lifecycle.touch()
        msg_type, msg_session_id, msg_request_id, payload = result

        with log_context(session_id=msg_session_id, request_id=msg_request_id):
            if not await _apply_rate_limit(
                ws,
                msg_type,
                message_limiter,
                cancel_limiter,
                session_id=msg_session_id,
                request_id=msg_request_id,
            ):
                continue
            if msg_type in {"ping", "pong", "end"}:
                if await _handle_control_message(ws, msg_type, msg_session_id, msg_request_id):
                    break
                continue
            session_id = await _dispatch_session_message(
                ws,
                msg_type=msg_type,
                payload=payload,
                msg_session_id=msg_session_id,
                msg_request_id=msg_request_id,
                active_session_id=session_id,
                session_handler=session_handler,
                runtime_deps=runtime_deps,
            )

    return session_id


__all__ = ["run_message_loop"]
