"""Cancel test runner for request cancellation and recovery verification.

This module provides the core test logic for verifying that:
1. Cancel messages abort in-flight requests (done with cancelled=True)
2. The connection remains usable after cancellation
3. Subsequent requests complete successfully

The test flow:
1. Connect to server
2. Send start message
3. Wait for ACK, then immediately send cancel
4. Verify done response has cancelled=True
5. Wait post-cancel delay
6. Send second start message
7. Stream full response
8. Verify done response has cancelled=False and response is valid
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from typing import Any

import websockets

from tests.config import (
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    CANCEL_POST_WAIT_DEFAULT,
    CANCEL_RECV_TIMEOUT_DEFAULT,
)
from tests.helpers.fmt import (
    section_header,
    exchange_header,
    exchange_footer,
    format_user,
    format_assistant,
    format_metrics_inline,
    format_pass,
    format_fail,
    dim,
    bold,
    green,
    red,
)
from tests.helpers.metrics import SessionContext, StreamState
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.websocket import (
    build_start_payload,
    connect_with_retries,
    create_tracker,
    finalize_metrics,
    send_client_end,
    iter_messages,
    dispatch_message,
)

CANCEL_TEST_MESSAGE = "hey there! tell me a story about a magical forest"


@dataclass
class CancelPhaseResult:
    """Result from the cancel phase of the test."""

    passed: bool
    cancelled: bool
    tokens_received: int
    chars_received: int
    ack_seen: bool
    error: str | None = None


@dataclass
class RecoveryPhaseResult:
    """Result from the recovery phase of the test."""

    passed: bool
    response_text: str
    metrics: dict[str, Any]
    error: str | None = None


# ============================================================================
# Cancel Phase Handlers
# ============================================================================


def _build_cancel_handlers(
    state: StreamState,
) -> dict[str, Any]:
    """Build message handlers for the cancel phase."""

    def handle_ack(msg: dict[str, Any]) -> bool:
        state.ack_seen = True
        return True

    def handle_toolcall(msg: dict[str, Any]) -> bool:
        state.toolcall_status = msg.get("status")
        state.toolcall_raw = msg.get("raw")
        return True

    def handle_token(msg: dict[str, Any]) -> bool:
        chunk = msg.get("text", "")
        if chunk:
            state.final_text += chunk
            state.chunks += 1
        return True

    def handle_final(msg: dict[str, Any]) -> bool:
        normalized = msg.get("normalized_text")
        if normalized:
            state.final_text = normalized
        return True

    def handle_done(msg: dict[str, Any]) -> dict[str, Any]:
        cancelled = bool(msg.get("cancelled"))
        return {"_done": True, "cancelled": cancelled}

    def handle_error(msg: dict[str, Any]) -> dict[str, Any]:
        return {"_done": True, "error": msg.get("message", "unknown error")}

    return {
        "ack": handle_ack,
        "toolcall": handle_toolcall,
        "token": handle_token,
        "final": handle_final,
        "done": handle_done,
        "error": handle_error,
    }


async def _run_cancel_phase(
    ws,
    ctx: SessionContext,
    user_msg: str,
    recv_timeout: float,
) -> CancelPhaseResult:
    """Execute the cancel phase: send start, wait for ACK, send cancel."""
    state = create_tracker()
    handlers = _build_cancel_handlers(state)

    # Send start message
    start_payload = build_start_payload(ctx, user_msg)
    await ws.send(json.dumps(start_payload))
    print(dim("  [cancel] sent start message..."))

    # Stream messages until ACK, then send cancel
    cancel_sent = False
    cancelled = False
    error: str | None = None

    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            result = await dispatch_message(
                msg,
                handlers,
                default=lambda m: True,
            )

            # Send cancel right after ACK
            if state.ack_seen and not cancel_sent:
                print(dim("  [cancel] received ACK"))
                await ws.send(json.dumps({"type": "cancel"}))
                cancel_sent = True
                print(dim("  [cancel] sent cancel message"))

            # Check if we're done
            if isinstance(result, dict) and result.get("_done"):
                cancelled = result.get("cancelled", False)
                error = result.get("error")
                break

    except asyncio.TimeoutError:
        error = f"timeout after {recv_timeout:.1f}s"
    except websockets.ConnectionClosed as exc:
        error = f"connection closed: {exc.code}"

    # Determine pass/fail
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


# ============================================================================
# Recovery Phase Handlers
# ============================================================================


def _build_recovery_handlers(
    state: StreamState,
) -> dict[str, Any]:
    """Build message handlers for the recovery phase."""

    def handle_ack(msg: dict[str, Any]) -> bool:
        state.ack_seen = True
        return True

    def handle_toolcall(msg: dict[str, Any]) -> bool:
        state.toolcall_status = msg.get("status")
        state.toolcall_raw = msg.get("raw")
        return True

    def handle_token(msg: dict[str, Any]) -> bool:
        chunk = msg.get("text", "")
        if chunk:
            if state.first_token_ts is None:
                import time
                state.first_token_ts = time.perf_counter()
            state.final_text += chunk
            state.chunks += 1
        return True

    def handle_final(msg: dict[str, Any]) -> bool:
        normalized = msg.get("normalized_text")
        if normalized:
            state.final_text = normalized
        return True

    def handle_done(msg: dict[str, Any]) -> dict[str, Any]:
        cancelled = bool(msg.get("cancelled"))
        metrics = finalize_metrics(state, cancelled)
        return {"_done": True, "cancelled": cancelled, "metrics": metrics}

    def handle_error(msg: dict[str, Any]) -> dict[str, Any]:
        return {"_done": True, "error": msg.get("message", "unknown error")}

    return {
        "ack": handle_ack,
        "toolcall": handle_toolcall,
        "token": handle_token,
        "final": handle_final,
        "done": handle_done,
        "error": handle_error,
    }


async def _run_recovery_phase(
    ws,
    ctx: SessionContext,
    user_msg: str,
    recv_timeout: float,
    post_cancel_wait: float,
) -> RecoveryPhaseResult:
    """Execute the recovery phase: wait, send start, stream full response."""
    # Wait before recovery
    print(dim(f"  [recovery] waiting {post_cancel_wait:.1f}s..."))
    await asyncio.sleep(post_cancel_wait)

    state = create_tracker()
    handlers = _build_recovery_handlers(state)

    # Send start message
    start_payload = build_start_payload(ctx, user_msg)
    await ws.send(json.dumps(start_payload))
    print(dim("  [recovery] sent start message..."))

    # Stream full response
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

    # Determine pass/fail: not cancelled and has response (text or toolcall)
    has_response = len(state.final_text) > 0 or state.toolcall_status is not None
    passed = not cancelled and has_response and error is None

    return RecoveryPhaseResult(
        passed=passed,
        response_text=state.final_text,
        metrics=metrics,
        error=error,
    )


# ============================================================================
# Public API
# ============================================================================


async def run_cancel_suite(
    ws_url: str,
    *,
    gender: str,
    personality: str,
    post_cancel_wait_s: float = CANCEL_POST_WAIT_DEFAULT,
    recv_timeout_s: float = CANCEL_RECV_TIMEOUT_DEFAULT,
) -> bool:
    """Run the cancel test suite.

    Args:
        ws_url: WebSocket URL with API key.
        gender: Persona gender for test messages.
        personality: Persona personality style.
        post_cancel_wait_s: Seconds to wait after cancel before recovery.
        recv_timeout_s: Timeout for each receive phase.

    Returns:
        True if all tests passed, False otherwise.
    """
    print(f"\n{section_header('CANCEL TEST')}")
    # Extract server URL for display (strip API key)
    display_url = ws_url.split("?")[0]
    print(dim(f"  server: {display_url}"))
    print(dim(f"  persona: {personality}/{gender}\n"))

    chat_prompt = select_chat_prompt(gender)
    session_id = str(uuid.uuid4())
    ctx = SessionContext(
        session_id=session_id,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
    )

    passed_count = 0
    failed_count = 0

    async with connect_with_retries(
        lambda: websockets.connect(
            ws_url,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        )
    ) as ws:
        # Phase 1: Cancel
        print(f"{bold('▶ CANCEL PHASE')}")
        cancel_result = await _run_cancel_phase(
            ws,
            ctx,
            CANCEL_TEST_MESSAGE,
            recv_timeout_s,
        )

        if cancel_result.passed:
            print(f"  {green('✓')} [cancel] {green('PASS')}")
            passed_count += 1
        else:
            reason = cancel_result.error or "cancelled=False"
            print(f"  {red('✗')} [cancel] {red('FAIL')}: {reason}")
            failed_count += 1

        # Phase 2: Recovery (only if cancel phase didn't break connection)
        print(f"\n{bold('▶ RECOVERY PHASE')}")
        recovery_result = await _run_recovery_phase(
            ws,
            ctx,
            CANCEL_TEST_MESSAGE,
            recv_timeout_s,
            post_cancel_wait_s,
        )

        if recovery_result.passed:
            # Print exchange details
            print(exchange_header())
            print(f"  {format_user(CANCEL_TEST_MESSAGE)}")
            response_preview = recovery_result.response_text[:80]
            if len(recovery_result.response_text) > 80:
                response_preview += "..."
            print(f"  {format_assistant(response_preview)}")
            print(f"  {format_metrics_inline(recovery_result.metrics)}")
            print(exchange_footer())
            print(f"  {green('✓')} [recovery] {green('PASS')}")
            passed_count += 1
        else:
            reason = recovery_result.error or "empty response"
            print(f"  {red('✗')} [recovery] {red('FAIL')}: {reason}")
            failed_count += 1

        # Send end frame
        await send_client_end(ws)

    # Summary
    print(f"\n{dim('─' * 40)}")
    total = passed_count + failed_count
    if failed_count == 0:
        print(f"  All {total} tests passed")
    else:
        print(f"  {passed_count} passed, {failed_count} failed")

    return failed_count == 0


__all__ = ["run_cancel_suite"]
