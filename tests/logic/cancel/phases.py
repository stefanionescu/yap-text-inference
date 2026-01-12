"""Phase execution functions for cancel test.

This module provides async functions for each test phase:
- Cancel phase: send start, wait, send cancel, verify cancelled=True
- Drain phase: verify no spurious messages after cancel
- Recovery phase: send another request, verify full response
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import websockets

from tests.helpers.fmt import dim
from tests.helpers.metrics import SessionContext, StreamState
from tests.helpers.websocket import (
    build_start_payload,
    create_tracker,
    finalize_metrics,
    iter_messages,
    dispatch_message,
)

from .handlers import build_cancel_handlers, build_recovery_handlers
from .types import CancelPhaseResult, DrainPhaseResult, RecoveryPhaseResult

logger = logging.getLogger(__name__)


async def run_cancel_phase(
    ws,
    ctx: SessionContext,
    user_msg: str,
    recv_timeout: float,
    cancel_delay: float,
) -> CancelPhaseResult:
    """Execute the cancel phase: send start, wait, then send cancel.

    Args:
        ws: WebSocket connection.
        ctx: Session context for building payloads.
        user_msg: User message to send.
        recv_timeout: Timeout for receiving messages.
        cancel_delay: Seconds to wait after ACK before sending cancel.

    Returns:
        Result of the cancel phase.
    """
    state = create_tracker()
    handlers = build_cancel_handlers(state)

    start_payload = build_start_payload(ctx, user_msg)
    await ws.send(json.dumps(start_payload))
    print(dim("  [cancel] sent start message..."))

    cancel_sent = False
    cancelled = False
    error: str | None = None
    ack_time: float | None = None

    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            result = await dispatch_message(
                msg,
                handlers,
                default=lambda m: True,
            )

            if state.ack_seen and ack_time is None:
                ack_time = time.perf_counter()
                print(dim("  [cancel] received ACK, waiting before cancel..."))

            # Send cancel after delay from ACK
            if ack_time is not None and not cancel_sent:
                elapsed = time.perf_counter() - ack_time
                if elapsed >= cancel_delay:
                    await ws.send(json.dumps({"type": "cancel"}))
                    cancel_sent = True
                    print(dim(f"  [cancel] sent cancel after {elapsed:.1f}s"))

            if isinstance(result, dict) and result.get("_done"):
                cancelled = result.get("cancelled", False)
                error = result.get("error")
                break

    except asyncio.TimeoutError:
        error = f"timeout after {recv_timeout:.1f}s"
    except websockets.ConnectionClosed as exc:
        error = f"connection closed: {exc.code}"

    passed = cancelled and error is None

    status_parts = [f"cancelled={cancelled}"]
    if state.chunks > 0:
        status_parts.append(f"tokens={state.chunks}")
    if len(state.final_text) > 0:
        status_parts.append(f"chars={len(state.final_text)}")
    print(dim(f"  [cancel] received done ({', '.join(status_parts)})"))

    return CancelPhaseResult(
        passed=passed,
        cancelled=cancelled,
        tokens_received=state.chunks,
        chars_received=len(state.final_text),
        ack_seen=state.ack_seen,
        error=error,
    )


async def run_drain_phase(
    ws,
    drain_timeout: float,
) -> DrainPhaseResult:
    """Verify no spurious messages arrive after cancel acknowledgement.

    This phase waits for drain_timeout seconds. If ANY message arrives,
    the test fails. Success means timing out with no messages received.

    Args:
        ws: WebSocket connection.
        drain_timeout: Seconds to wait for potential spurious messages.

    Returns:
        Result of the drain phase.
    """
    print(dim(f"  [drain] checking for spurious messages ({drain_timeout:.1f}s)..."))
    spurious_count = 0
    spurious_types: list[str] = []

    try:
        async for msg in iter_messages(ws, timeout=drain_timeout):
            msg_type = msg.get("type", "unknown")
            spurious_count += 1
            spurious_types.append(msg_type)
            logger.warning("Spurious message after cancel: type=%s", msg_type)
    except asyncio.TimeoutError:
        # Timeout is expected and means success
        pass
    except websockets.ConnectionClosed:
        # Connection closed is acceptable during drain
        pass

    passed = spurious_count == 0
    error = None
    if not passed:
        error = f"received {spurious_count} spurious message(s): {spurious_types}"

    if passed:
        print(dim("  [drain] no spurious messages"))
    else:
        print(dim(f"  [drain] FAILED: {error}"))

    return DrainPhaseResult(
        passed=passed,
        spurious_messages=spurious_count,
        error=error,
    )


async def run_recovery_phase(
    ws,
    ctx: SessionContext,
    user_msg: str,
    recv_timeout: float,
    post_cancel_wait: float,
) -> RecoveryPhaseResult:
    """Execute the recovery phase: wait, send start, stream full response.

    Args:
        ws: WebSocket connection.
        ctx: Session context for building payloads.
        user_msg: User message to send.
        recv_timeout: Timeout for receiving messages.
        post_cancel_wait: Seconds to wait before sending recovery request.

    Returns:
        Result of the recovery phase.
    """
    print(dim(f"  [recovery] waiting {post_cancel_wait:.1f}s before request..."))
    await asyncio.sleep(post_cancel_wait)

    state = create_tracker()
    handlers = build_recovery_handlers(state)

    start_payload = build_start_payload(ctx, user_msg)
    await ws.send(json.dumps(start_payload))
    print(dim("  [recovery] sent start message..."))

    cancelled = False
    error: str | None = None
    metrics: dict[str, Any] = {}

    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            result = await dispatch_message(
                msg,
                handlers,
                default=lambda m: True,
            )

            if isinstance(result, dict) and result.get("_done"):
                cancelled = result.get("cancelled", False)
                error = result.get("error")
                metrics = result.get("metrics", {})
                break

    except asyncio.TimeoutError:
        error = f"timeout after {recv_timeout:.1f}s"
        metrics = finalize_metrics(state, cancelled=True)
    except websockets.ConnectionClosed as exc:
        error = f"connection closed: {exc.code}"
        metrics = finalize_metrics(state, cancelled=True)

    has_response = len(state.final_text) > 0 or state.toolcall_status is not None
    passed = not cancelled and has_response and error is None

    return RecoveryPhaseResult(
        passed=passed,
        response_text=state.final_text,
        metrics=metrics,
        error=error,
    )


__all__ = ["run_cancel_phase", "run_drain_phase", "run_recovery_phase"]
