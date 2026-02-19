"""Primary WebSocket connection handler orchestration.

This module contains the main WebSocket connection handler that serves as
the entry point for all client connections. It orchestrates connection setup,
message-loop dispatch, and cleanup on disconnect.
"""

from __future__ import annotations

import logging
import contextlib

from fastapi import WebSocket, WebSocketDisconnect

from src.runtime.dependencies import RuntimeDeps

from .auth import authenticate_websocket
from .lifecycle import WebSocketLifecycle
from .message_loop import run_message_loop
from ...telemetry.traces import session_span
from ..limits import SlidingWindowRateLimiter
from ...telemetry.errors import get_error_type
from ...telemetry.instruments import get_metrics
from .errors import send_error, reject_connection
from .disconnects import is_expected_ws_disconnect
from ...logging import set_log_context, reset_log_context
from ...telemetry.sentry import capture_error, add_breadcrumb
from ...config.websocket import (
    WS_ERROR_INTERNAL,
    WS_CLOSE_BUSY_CODE,
    WS_ERROR_AUTH_FAILED,
    WS_ERROR_SERVER_BUSY,
    WS_CLOSE_UNAUTHORIZED_CODE,
)
from ...config import (
    WS_CANCEL_WINDOW_SECONDS,
    WS_MAX_CANCELS_PER_WINDOW,
    WS_MESSAGE_WINDOW_SECONDS,
    WS_MAX_MESSAGES_PER_WINDOW,
    CACHE_RESET_MIN_SESSION_SECONDS,
)

logger = logging.getLogger(__name__)


def _is_expected_disconnect_exception(exc: BaseException, lifecycle: WebSocketLifecycle) -> bool:
    """Return True when connection teardown is expected and non-actionable."""

    return lifecycle.idle_timed_out() or is_expected_ws_disconnect(exc)


async def _prepare_connection(ws: WebSocket, runtime_deps: RuntimeDeps) -> bool:
    """Authenticate and admit a WebSocket connection."""
    connections = runtime_deps.connections
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


async def _cleanup_session(runtime_deps: RuntimeDeps, session_id: str | None) -> float:
    """Clean up session resources on disconnect and return duration."""
    session_handler = runtime_deps.session_handler
    duration = 0.0
    if session_id:
        duration = session_handler.get_session_duration(session_id)
    await session_handler.abort_session_requests(session_id, clear_state=True)
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


async def _finalize_connection(
    ws: WebSocket,
    runtime_deps: RuntimeDeps,
    lifecycle: WebSocketLifecycle | None,
    session_id: str | None,
    admitted: bool,
    generation_count: int = 0,
) -> None:
    """Handle teardown actions after the connection loop exits."""
    m = get_metrics()
    connections = runtime_deps.connections
    if lifecycle is not None:
        with contextlib.suppress(Exception):
            await lifecycle.stop()

    session_duration = 0.0
    try:
        session_duration = await _cleanup_session(runtime_deps, session_id)
    except Exception as exc:  # noqa: BLE001
        capture_error(exc)
        m.errors_total.add(1, {"error.type": "cleanup_failed"})
        logger.exception("WebSocket cleanup failed")

    if not admitted:
        return

    m.active_connections.add(-1)
    m.connection_duration.record(session_duration)
    m.session_churn_total.add(1)
    if generation_count:
        m.generations_per_session.record(generation_count)

    with contextlib.suppress(Exception):
        await connections.disconnect(ws)

    remaining = connections.get_connection_count()
    logger.info("WebSocket connection closed. Active: %s", remaining)

    should_reset = session_id is not None and session_duration >= CACHE_RESET_MIN_SESSION_SECONDS
    if should_reset:
        with contextlib.suppress(Exception):
            triggered = await runtime_deps.reset_engine_caches("long_session", force=True)
            if triggered:
                m.cache_resets_total.add(1)
                add_breadcrumb("Cache reset", category="engine")
                logger.info(
                    "cache reset after long session_id=%s duration=%.1fs",
                    session_id,
                    session_duration,
                )

    if remaining == 0:
        with contextlib.suppress(Exception):
            await runtime_deps.clear_caches_on_disconnect()


async def handle_websocket_connection(ws: WebSocket, runtime_deps: RuntimeDeps) -> None:
    """Handle WebSocket connection and route messages to appropriate handlers."""
    client = ws.client
    client_id = f"{client.host}:{client.port}" if client else "unknown"
    tokens = set_log_context(client_id=client_id)
    m = get_metrics()
    try:
        lifecycle: WebSocketLifecycle | None = None
        admitted = False

        if not await _prepare_connection(ws, runtime_deps):
            return

        admitted = True
        m.active_connections.add(1)
        add_breadcrumb("Connection accepted", category="server")
        session_id: str | None = None
        message_limiter, cancel_limiter = _create_rate_limiters()
        lifecycle = WebSocketLifecycle(ws)
        lifecycle.start()

        logger.info(
            "WebSocket connection accepted. Active: %s",
            runtime_deps.connections.get_connection_count(),
        )

        try:
            with session_span(session_id=session_id or "", client_id=client_id):
                session_id = await run_message_loop(
                    ws,
                    lifecycle,
                    message_limiter,
                    cancel_limiter,
                    runtime_deps,
                )
        except WebSocketDisconnect:
            pass
        except Exception as exc:  # noqa: BLE001
            if _is_expected_disconnect_exception(exc, lifecycle):
                logger.info("WebSocket disconnected (%s)", exc.__class__.__name__)
            else:
                capture_error(exc)
                m.errors_total.add(1, {"error.type": get_error_type(exc)})
                logger.exception("WebSocket error")
                with contextlib.suppress(Exception):
                    await send_error(
                        ws,
                        session_id=session_id,
                        request_id=None,
                        error_code=WS_ERROR_INTERNAL,
                        message="An unexpected server error occurred.",
                        reason_code="internal_exception",
                    )
        finally:
            await _finalize_connection(ws, runtime_deps, lifecycle, session_id, admitted)
    finally:
        reset_log_context(tokens)


__all__ = ["handle_websocket_connection"]
