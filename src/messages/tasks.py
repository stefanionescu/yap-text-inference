"""Session task supervision for background message execution."""

from __future__ import annotations

import time
import asyncio
import logging
import contextlib
from typing import Any
from fastapi import WebSocket
from collections.abc import Awaitable
from src.state.session import SessionState
from src.telemetry.traces import request_span
from src.telemetry.sentry import capture_error
from src.telemetry.errors import get_error_type
from src.telemetry.instruments import get_metrics
from src.config.websocket import WS_ERROR_INTERNAL
from src.handlers.websocket.errors import send_error
from src.handlers.session.manager import SessionHandler
from src.handlers.websocket.disconnects import is_expected_ws_disconnect
from src.telemetry.phases import record_phase_error, record_phase_latency

logger = logging.getLogger(__name__)


async def _run_with_supervision(
    ws: WebSocket,
    operation: Awaitable[Any],
    *,
    request_id: str,
    state: SessionState,
    session_handler: SessionHandler,
) -> None:
    t0 = time.perf_counter()
    model = str(state.meta.get("chat_model") or state.meta.get("tool_model") or "")
    client_id = str(state.meta.get("client_id") or "")
    with request_span(
        request_id=request_id,
        session_id=state.session_id,
        client_id=client_id,
        model=model,
    ):
        try:
            await operation
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - defensive task wrapper
            if is_expected_ws_disconnect(exc):
                logger.info("Session task ended after disconnect (%s)", exc.__class__.__name__)
                return
            capture_error(exc)
            error_type = get_error_type(exc)
            get_metrics().errors_total.add(1, {"error.type": error_type})
            record_phase_error("turn", error_type)
            logger.exception("Session task failed")
            with contextlib.suppress(Exception):
                await send_error(
                    ws,
                    code=WS_ERROR_INTERNAL,
                    message="An unexpected server error occurred.",
                )
        finally:
            record_phase_latency("turn", time.perf_counter() - t0)
            with contextlib.suppress(Exception):
                await session_handler.complete_request(state, request_id)


async def spawn_session_task(
    ws: WebSocket,
    state: SessionState,
    *,
    request_id: str,
    operation: Awaitable[Any],
    session_handler: SessionHandler,
) -> asyncio.Task[Any] | None:
    """Create, supervise, and track a session-scoped background task."""
    started = await session_handler.begin_request(state, request_id)
    if not started:
        return None

    task = asyncio.create_task(
        _run_with_supervision(
            ws,
            operation,
            request_id=request_id,
            state=state,
            session_handler=session_handler,
        )
    )
    await session_handler.track_request_task(state, request_id=request_id, task=task)
    return task


__all__ = ["spawn_session_task"]
