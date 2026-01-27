"""Client flow orchestration for cancel test.

This module provides async functions that orchestrate the full lifecycle
of each client type:
- Canceling client: cancel phase -> drain phase -> recovery phase
- Normal client: stream full response -> wait for coordination
"""

from __future__ import annotations

import json
import asyncio
from typing import Any

import websockets

from tests.helpers.fmt import dim
from tests.helpers.metrics import SessionContext
from tests.config import DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.helpers.websocket import (
    iter_messages,
    create_tracker,
    send_client_end,
    dispatch_message,
    finalize_metrics,
    build_start_payload,
    connect_with_retries,
)

from .handlers import build_recovery_handlers
from .phases import run_drain_phase, run_cancel_phase, run_recovery_phase
from .types import DrainPhaseResult, CancelPhaseResult, CancelClientResult, NormalClientResult, RecoveryPhaseResult


async def run_normal_client(
    ws_url: str,
    ctx: SessionContext,
    client_id: int,
    user_msg: str,
    recv_timeout: float,
    wait_for_recovery: asyncio.Event,
) -> NormalClientResult:
    """Run a client that completes inference normally and waits for coordination.

    Args:
        ws_url: WebSocket URL with API key.
        ctx: Session context for building payloads.
        client_id: Identifier for this client.
        user_msg: User message to send.
        recv_timeout: Timeout for receiving messages.
        wait_for_recovery: Event to wait on before disconnecting.

    Returns:
        Result of the normal client flow.
    """
    label = f"client-{client_id}"

    try:
        async with connect_with_retries(
            lambda: websockets.connect(
                ws_url,
                max_queue=None,
                ping_interval=DEFAULT_WS_PING_INTERVAL,
                ping_timeout=DEFAULT_WS_PING_TIMEOUT,
            )
        ) as ws:
            state = create_tracker()
            handlers = build_recovery_handlers(state)

            start_payload = build_start_payload(ctx, user_msg)
            await ws.send(json.dumps(start_payload))
            print(dim(f"  [{label}] sent start message..."))

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

            if passed:
                print(dim(f"  [{label}] completed, waiting for cancel recovery..."))
            else:
                reason = error or "empty response or cancelled"
                print(dim(f"  [{label}] FAILED: {reason}"))

            # Wait for the canceling client to complete recovery
            await wait_for_recovery.wait()

            await send_client_end(ws)

            return NormalClientResult(
                client_id=client_id,
                passed=passed,
                response_text=state.final_text,
                metrics=metrics,
                error=error,
            )

    except Exception as exc:  # noqa: BLE001
        return NormalClientResult(
            client_id=client_id,
            passed=False,
            response_text="",
            metrics={},
            error=f"connection failed: {exc}",
        )


async def run_canceling_client(
    ws_url: str,
    ctx: SessionContext,
    user_msg: str,
    cancel_delay: float,
    drain_timeout: float,
    post_cancel_wait: float,
    recv_timeout: float,
    recovery_done: asyncio.Event,
) -> CancelClientResult:
    """Run the client that performs cancel, drain verification, and recovery.

    Args:
        ws_url: WebSocket URL with API key.
        ctx: Session context for building payloads.
        user_msg: User message to send.
        cancel_delay: Seconds to wait before sending cancel.
        drain_timeout: Seconds to verify no spurious messages.
        post_cancel_wait: Seconds to wait before recovery request.
        recv_timeout: Timeout for receiving messages.
        recovery_done: Event to signal when recovery completes.

    Returns:
        Combined result of cancel, drain, and recovery phases.
    """
    cancel_result = CancelPhaseResult(
        passed=False, cancelled=False, tokens_received=0,
        chars_received=0, ack_seen=False, error="connection failed"
    )
    drain_result = DrainPhaseResult(passed=False, spurious_messages=0, error="skipped")
    recovery_result = RecoveryPhaseResult(
        passed=False, response_text="", metrics={}, error="skipped"
    )

    try:
        async with connect_with_retries(
            lambda: websockets.connect(
                ws_url,
                max_queue=None,
                ping_interval=DEFAULT_WS_PING_INTERVAL,
                ping_timeout=DEFAULT_WS_PING_TIMEOUT,
            )
        ) as ws:
            # Phase 1: Cancel
            cancel_result = await run_cancel_phase(
                ws, ctx, user_msg, recv_timeout, cancel_delay
            )

            # Phase 2: Drain (only if cancel succeeded)
            if cancel_result.passed:
                drain_result = await run_drain_phase(ws, drain_timeout)
            else:
                drain_result = DrainPhaseResult(
                    passed=False, spurious_messages=0, error="skipped due to cancel failure"
                )

            # Phase 3: Recovery (only if drain succeeded)
            if drain_result.passed:
                recovery_result = await run_recovery_phase(
                    ws, ctx, user_msg, recv_timeout, post_cancel_wait
                )
            else:
                recovery_result = RecoveryPhaseResult(
                    passed=False, response_text="", metrics={}, error="skipped due to drain failure"
                )

            # Signal completion so normal clients can disconnect
            recovery_done.set()

            await send_client_end(ws)

    except Exception as exc:  # noqa: BLE001
        cancel_result = CancelPhaseResult(
            passed=False, cancelled=False, tokens_received=0,
            chars_received=0, ack_seen=False, error=f"connection failed: {exc}"
        )
        recovery_done.set()

    return CancelClientResult(
        cancel_phase=cancel_result,
        drain_phase=drain_result,
        recovery_phase=recovery_result,
    )


__all__ = ["run_normal_client", "run_canceling_client"]
