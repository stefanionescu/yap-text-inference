"""WebSocket message loop and dispatch helpers."""

from __future__ import annotations

import time
import logging
import contextlib
from typing import Any
from fastapi import WebSocket
from .errors import send_error
from ...logging import log_context
from .helpers import safe_send_flat
from .parser import parse_client_message
from .lifecycle import WebSocketLifecycle
from src.state.session import SessionState
from ..limits import SlidingWindowRateLimiter
from ...messages.turn import handle_turn_message
from ...telemetry.instruments import get_metrics
from src.runtime.dependencies import RuntimeDeps
from .disconnects import is_expected_ws_disconnect
from ...messages.cancel import handle_cancel_message
from src.handlers.session.manager import SessionHandler
from .limits import consume_limiter, select_rate_limiter
from src.handlers.session.requests import has_running_task
from ...telemetry.phases import record_phase_error, record_phase_latency
from ...config.websocket import WS_STATUS_OK, WS_ERROR_INVALID_MESSAGE, WS_CLOSE_CLIENT_REQUEST_CODE

logger = logging.getLogger(__name__)


async def _handle_control_message(
    ws: WebSocket,
    msg_type: str,
) -> bool:
    """Process ping/pong/end messages; return True if connection should close."""
    if msg_type == "ping":
        await safe_send_flat(ws, "pong")
        return False
    if msg_type == "pong":
        return False
    if msg_type == "end":
        logger.info("WS recv: end")
        await safe_send_flat(ws, "done", status=WS_STATUS_OK)
        with contextlib.suppress(Exception):
            await ws.close(code=WS_CLOSE_CLIENT_REQUEST_CODE)
        return True
    return False


async def _parse_incoming(ws: WebSocket, raw_msg: str) -> dict[str, Any] | None:
    """Parse raw text into a flat message dict or None on error."""
    t0 = time.perf_counter()
    try:
        parsed = parse_client_message(raw_msg)
        record_phase_latency("parse", time.perf_counter() - t0)
        return parsed
    except ValueError as exc:
        record_phase_latency("parse", time.perf_counter() - t0)
        record_phase_error("parse", "invalid_payload")
        await send_error(ws, code=WS_ERROR_INVALID_MESSAGE, message=str(exc))
        return None


async def _apply_rate_limit(
    ws: WebSocket,
    msg_type: str,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
) -> bool:
    limiter, label = select_rate_limiter(msg_type, message_limiter, cancel_limiter)
    if limiter is None:
        return True
    return await consume_limiter(ws, limiter, label)


async def _handle_turn_command(
    ws: WebSocket,
    msg_type: str,
    msg: dict[str, Any],
    state: SessionState,
    started: bool,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> bool:
    """Handle start/message commands and return updated started flag."""
    if msg_type == "start":
        if started:
            await send_error(
                ws,
                code=WS_ERROR_INVALID_MESSAGE,
                message="start may only be sent once per connection; use 'message' for subsequent turns.",
            )
            return True
        get_metrics().requests_total.add(1, {"status": "started"})
        await handle_turn_message(
            ws,
            msg,
            state,
            msg_type="start",
            session_handler=session_handler,
            runtime_deps=runtime_deps,
        )
        return True

    if not started:
        await send_error(
            ws,
            code=WS_ERROR_INVALID_MESSAGE,
            message="no active session; send 'start' first.",
        )
        return False

    if msg_type != "message":
        return started

    get_metrics().requests_total.add(1, {"status": "continued"})
    if has_running_task(state):
        await session_handler.abort_session_requests(state)
    await handle_turn_message(
        ws,
        msg,
        state,
        msg_type="message",
        session_handler=session_handler,
        runtime_deps=runtime_deps,
    )
    return True


async def _dispatch_session_message(
    ws: WebSocket,
    *,
    msg_type: str,
    msg: dict[str, Any],
    state: SessionState,
    started: bool,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> bool:
    """Dispatch a session message. Returns the new 'started' flag."""
    if msg_type in {"start", "message"}:
        return await _handle_turn_command(
            ws,
            msg_type,
            msg,
            state,
            started,
            session_handler=session_handler,
            runtime_deps=runtime_deps,
        )
    if msg_type == "cancel":
        get_metrics().cancellation_total.add(1)
        logger.info("WS recv: cancel")
        await handle_cancel_message(ws, state, session_handler=session_handler)
        return True
    await send_error(
        ws,
        code=WS_ERROR_INVALID_MESSAGE,
        message=f"Message type '{msg_type}' is not supported.",
    )
    return started


async def run_message_loop(
    ws: WebSocket,
    lifecycle: WebSocketLifecycle,
    message_limiter: SlidingWindowRateLimiter,
    cancel_limiter: SlidingWindowRateLimiter,
    runtime_deps: RuntimeDeps,
) -> SessionState:
    """Receive, validate, and dispatch client messages.

    Creates a per-connection SessionState and passes it to all handlers.
    Returns the state for cleanup.
    """
    client = ws.client
    client_id = f"{client.host}:{client.port}" if client else "unknown"
    state = SessionState(meta={"client_id": client_id})
    started = False
    session_handler = runtime_deps.session_handler

    while True:
        try:
            raw_msg = await ws.receive_text()
        except Exception as exc:  # noqa: BLE001 - narrowed by classification helper
            if lifecycle.idle_timed_out() or is_expected_ws_disconnect(exc):
                break
            raise

        msg = await _parse_incoming(ws, raw_msg)
        if msg is None:
            continue

        lifecycle.touch()
        msg_type = msg["type"]

        with log_context():
            if not await _apply_rate_limit(ws, msg_type, message_limiter, cancel_limiter):
                continue
            if msg_type in {"ping", "pong", "end"}:
                if await _handle_control_message(ws, msg_type):
                    break
                continue
            started = await _dispatch_session_message(
                ws,
                msg_type=msg_type,
                msg=msg,
                state=state,
                started=started,
                session_handler=session_handler,
                runtime_deps=runtime_deps,
            )

    return state


__all__ = ["run_message_loop"]
