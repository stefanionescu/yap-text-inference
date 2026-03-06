"""Session task supervision for background message execution."""

from __future__ import annotations

import asyncio
import logging
import contextlib
from typing import Any
from collections.abc import Awaitable
from fastapi import WebSocket
from src.state.session import SessionState
from src.telemetry.sentry import capture_error
from src.telemetry.errors import get_error_type
from src.telemetry.instruments import get_metrics
from src.handlers.session.manager import SessionHandler
from src.handlers.websocket.errors import send_error
from src.handlers.websocket.disconnects import is_expected_ws_disconnect
from src.config.websocket import WS_ERROR_INTERNAL

logger = logging.getLogger(__name__)


async def _run_with_supervision(
    ws: WebSocket,
    operation: Awaitable[Any],
) -> None:
    try:
        await operation
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001 - defensive task wrapper
        if is_expected_ws_disconnect(exc):
            logger.info("Session task ended after disconnect (%s)", exc.__class__.__name__)
            return
        capture_error(exc)
        get_metrics().errors_total.add(1, {"error.type": get_error_type(exc)})
        logger.exception("Session task failed")
        with contextlib.suppress(Exception):
            await send_error(
                ws,
                code=WS_ERROR_INTERNAL,
                message="An unexpected server error occurred.",
            )


def spawn_session_task(
    ws: WebSocket,
    state: SessionState,
    *,
    operation: Awaitable[Any],
    session_handler: SessionHandler,
) -> asyncio.Task[Any]:
    """Create, supervise, and track a session-scoped background task."""
    task = asyncio.create_task(_run_with_supervision(ws, operation))
    session_handler.track_task(state, task)
    return task


__all__ = ["spawn_session_task"]
