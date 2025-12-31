"""WebSocket response draining for tool regression tests.

This module handles the complex state machine for draining websocket responses
during tool test execution. The main entry point is `drain_response`, which
collects frames until a turn completes.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any

from tests.helpers.message import iter_messages

from .types import TurnResult


@dataclass
class DrainState:
    """Mutable state tracked during response draining."""

    tool_status: str | None = None
    tool_raw: Any = None
    chat_seen: bool = False
    done: bool = False
    cancelled: bool = False
    error: dict[str, Any] | None = None
    first_tool_frame_s: float | None = None
    last_tool_frame_s: float | None = None
    tool_decision_received: bool = False


@dataclass
class DrainConfig:
    """Configuration for response draining."""

    timeout_s: float
    chat_idle_timeout_s: float | None
    start_ts: float = field(default_factory=time.perf_counter)

    @property
    def tool_deadline(self) -> float:
        return self.start_ts + self.timeout_s


# ============================================================================
# Internal Helpers
# ============================================================================


async def _close_connection(ws, *, reason: str | None = None) -> None:
    """Attempt to close the websocket connection gracefully."""
    import inspect

    close = getattr(ws, "close", None)
    if close is None:
        return
    try:
        if reason is None:
            result = close()
        else:
            try:
                result = close(reason=reason)
            except TypeError:
                result = close()
        if inspect.isawaitable(result):
            await result
    except Exception:
        pass


def _tool_status_to_bool(status: str | None) -> bool | None:
    """Convert tool status string to boolean."""
    if status is None:
        return None
    lowered = status.lower()
    if lowered == "yes":
        return True
    if lowered == "no":
        return False
    return None


def _handle_toolcall(msg: dict[str, Any], state: DrainState, cfg: DrainConfig) -> None:
    """Handle a toolcall message."""
    elapsed = time.perf_counter() - cfg.start_ts
    if state.first_tool_frame_s is None:
        state.first_tool_frame_s = elapsed
    state.last_tool_frame_s = elapsed
    state.tool_decision_received = True
    state.tool_status = str(msg.get("status") or "").strip().lower()
    state.tool_raw = msg.get("raw")


def _process_message(msg: dict[str, Any], state: DrainState, cfg: DrainConfig) -> bool:
    """Process a single message and update state.
    
    Returns True if we should stop processing (done/error), False to continue.
    """
    msg_type = msg.get("type")

    if msg_type == "ack":
        return False

    if msg_type == "toolcall":
        _handle_toolcall(msg, state, cfg)
        return False

    if msg_type in {"token", "final"}:
        state.chat_seen = True
        return False

    if msg_type == "done":
        state.done = True
        state.cancelled = bool(msg.get("cancelled"))
        return True

    if msg_type == "error":
        state.error = msg
        return True

    return False


async def _get_message_with_timeout(
    messages,
    state: DrainState,
    cfg: DrainConfig,
) -> dict[str, Any]:
    """Get the next message with appropriate timeout.
    
    Raises StopAsyncIteration if the stream ends.
    Raises asyncio.TimeoutError if timeout occurs.
    """
    if not state.tool_decision_received:
        remaining = cfg.tool_deadline - time.perf_counter()
        timeout = max(0.0, remaining)
    elif cfg.chat_idle_timeout_s is not None:
        timeout = cfg.chat_idle_timeout_s
    else:
        timeout = None

    next_msg = messages.__anext__()
    if timeout is None:
        return await next_msg
    return await asyncio.wait_for(next_msg, timeout)


async def _receive_next_message(
    ws,
    messages,
    state: DrainState,
    cfg: DrainConfig,
) -> TurnResult | None:
    """Check if we've timed out before the tool decision arrived.
    
    Returns a TurnResult if timeout occurred, None to continue.
    """
    if state.tool_decision_received:
        return None

    remaining = cfg.tool_deadline - time.perf_counter()
    if remaining <= 0:
        await _close_connection(ws, reason="tool_timeout")
        return _build_timeout_result(state, cfg, is_tool_timeout=True)

    return None


def _build_timeout_result(
    state: DrainState,
    cfg: DrainConfig,
    *,
    is_tool_timeout: bool,
) -> TurnResult:
    """Build a timeout TurnResult."""
    if is_tool_timeout:
        reason = "timeout"
        detail = f"tool response not received within {cfg.timeout_s:.1f}s"
    else:
        reason = "chat_timeout"
        detail = f"no chat frames within {cfg.chat_idle_timeout_s:.1f}s after tool response"

    return TurnResult(
        ok=False,
        tool_called=None,
        tool_status=state.tool_status,
        tool_raw=state.tool_raw,
        chat_seen=state.chat_seen,
        reason=reason,
        detail=detail,
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


def _build_error_result(state: DrainState) -> TurnResult:
    """Build a server error TurnResult."""
    return TurnResult(
        ok=False,
        tool_called=None,
        tool_status=None,
        tool_raw=None,
        chat_seen=state.chat_seen,
        reason="server_error",
        detail=json.dumps(state.error, ensure_ascii=False),
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


def _build_incomplete_result(state: DrainState) -> TurnResult:
    """Build an incomplete stream TurnResult."""
    return TurnResult(
        ok=False,
        tool_called=None,
        tool_status=state.tool_status,
        tool_raw=state.tool_raw,
        chat_seen=state.chat_seen,
        reason="incomplete",
        detail="stream ended before 'done'",
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


def _build_cancelled_result(state: DrainState) -> TurnResult:
    """Build a cancelled TurnResult."""
    return TurnResult(
        ok=False,
        tool_called=None,
        tool_status=state.tool_status,
        tool_raw=state.tool_raw,
        chat_seen=state.chat_seen,
        reason="cancelled",
        detail="server reported cancellation",
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


def _build_invalid_status_result(state: DrainState) -> TurnResult:
    """Build a TurnResult for invalid tool status."""
    if state.tool_status is None:
        reason = "chat_only" if state.chat_seen else "no_tool_response"
        detail = (
            "received chat output but no toolcall"
            if state.chat_seen
            else "no frames received"
        )
    else:
        reason = "invalid_tool_status"
        detail = f"toolcall status '{state.tool_status}' is not yes/no"

    return TurnResult(
        ok=False,
        tool_called=None,
        tool_status=state.tool_status,
        tool_raw=state.tool_raw,
        chat_seen=state.chat_seen,
        reason=reason,
        detail=detail,
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


def _finalize_state(state: DrainState) -> TurnResult:
    """Convert final state into a TurnResult."""
    if state.error:
        return _build_error_result(state)

    if not state.done:
        return _build_incomplete_result(state)

    if state.cancelled:
        return _build_cancelled_result(state)

    tool_bool = _tool_status_to_bool(state.tool_status)
    if tool_bool is None:
        return _build_invalid_status_result(state)

    return TurnResult(
        ok=True,
        tool_called=tool_bool,
        tool_status=state.tool_status,
        tool_raw=state.tool_raw,
        chat_seen=state.chat_seen,
        ttfb_s=state.first_tool_frame_s,
        total_s=state.last_tool_frame_s,
    )


# ============================================================================
# Public API
# ============================================================================


async def drain_response(ws, cfg: DrainConfig) -> TurnResult:
    """Drain websocket frames until the server finishes the turn.
    
    The timeout applies only to the TOOL response. Once the tool decision
    arrives, we continue waiting for chat to flush without enforcing the
    per-turn timeout.
    
    Args:
        ws: Open WebSocket connection.
        cfg: Drain configuration with timeouts.
    
    Returns:
        TurnResult with the final state of the turn.
    """
    state = DrainState()
    messages = iter_messages(ws)

    while True:
        # Get next message with appropriate timeout
        result = await _receive_next_message(ws, messages, state, cfg)
        if result is not None:
            return result

        # Process the message and check if we're done
        try:
            msg = await _get_message_with_timeout(messages, state, cfg)
        except StopAsyncIteration:
            break

        if _process_message(msg, state, cfg):
            break

    return _finalize_state(state)


__all__ = ["DrainConfig", "DrainState", "drain_response"]
