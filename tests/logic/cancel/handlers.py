"""Message handler builders for cancel test phases.

This module provides factory functions that create message handlers
for the cancel and recovery phases. Handlers update StreamState as
messages arrive and signal completion when done.
"""

from __future__ import annotations

import time
from typing import Any
from tests.state import StreamState
from tests.helpers.websocket import finalize_metrics


def build_cancel_handlers(state: StreamState) -> dict[str, Any]:
    """Build message handlers for the cancel phase.

    These handlers track basic state without timing metrics since
    the cancel phase is interrupted before completion.

    Args:
        state: Mutable stream state to update as messages arrive.

    Returns:
        Dict mapping message types to handler functions.
    """

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
        return {"_done": True, "cancelled": False}

    def handle_cancelled(_: dict[str, Any]) -> dict[str, Any]:
        return {"_done": True, "cancelled": True}

    def handle_error(msg: dict[str, Any]) -> dict[str, Any]:
        return {"_done": True, "error": msg.get("message", "unknown error")}

    return {
        "ack": handle_ack,
        "toolcall": handle_toolcall,
        "token": handle_token,
        "final": handle_final,
        "done": handle_done,
        "cancelled": handle_cancelled,
        "error": handle_error,
    }


def build_recovery_handlers(state: StreamState) -> dict[str, Any]:
    """Build message handlers for the recovery phase.

    These handlers track full timing metrics since the recovery
    phase runs to completion.

    Args:
        state: Mutable stream state to update as messages arrive.

    Returns:
        Dict mapping message types to handler functions.
    """

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
        metrics = finalize_metrics(state, cancelled=False)
        return {"_done": True, "cancelled": False, "metrics": metrics}

    def handle_cancelled(_: dict[str, Any]) -> dict[str, Any]:
        metrics = finalize_metrics(state, cancelled=True)
        return {"_done": True, "cancelled": True, "metrics": metrics}

    def handle_error(msg: dict[str, Any]) -> dict[str, Any]:
        return {"_done": True, "error": msg.get("message", "unknown error")}

    return {
        "ack": handle_ack,
        "toolcall": handle_toolcall,
        "token": handle_token,
        "final": handle_final,
        "done": handle_done,
        "cancelled": handle_cancelled,
        "error": handle_error,
    }


__all__ = ["build_cancel_handlers", "build_recovery_handlers"]
