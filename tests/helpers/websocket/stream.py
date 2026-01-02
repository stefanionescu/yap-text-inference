"""Streaming token metrics tracking and consumption.

This module provides functions for tracking streaming token metrics and
consuming WebSocket response streams. Uses StreamState from metrics for
data storage.
"""

from __future__ import annotations

import time
from typing import Any

from tests.helpers.errors import StreamError
from tests.helpers.metrics import StreamState, round_ms
from tests.helpers.regex import contains_complete_sentence, word_count_at_least
from .message import iter_messages


# ============================================================================
# Internal Helpers
# ============================================================================


def _ms_since_sent(state: StreamState, timestamp: float | None) -> float | None:
    """Calculate milliseconds elapsed since the request was sent."""
    if timestamp is None:
        return None
    return (timestamp - state.sent_ts) * 1000.0


# ============================================================================
# Stream Tracking Functions
# ============================================================================


def create_tracker() -> StreamState:
    """Create a new stream tracker with current timestamp."""
    return StreamState()


def record_toolcall(state: StreamState) -> float | None:
    """Record the time-to-first-byte for tool call response."""
    now = time.perf_counter()
    state.toolcall_ttfb_ms = _ms_since_sent(state, now)
    return state.toolcall_ttfb_ms


def record_token(state: StreamState, chunk: str) -> dict[str, float | None]:
    """Record a streaming token and return any newly triggered metrics."""
    metrics: dict[str, float | None] = {}
    if not chunk:
        return metrics

    if state.first_token_ts is None:
        state.first_token_ts = time.perf_counter()
        metrics["chat_ttfb_ms"] = _ms_since_sent(state, state.first_token_ts)

    state.final_text += chunk
    
    if state.first_3_words_ts is None and word_count_at_least(state.final_text, 3):
        state.first_3_words_ts = time.perf_counter()
        metrics["time_to_first_3_words_ms"] = _ms_since_sent(state, state.first_3_words_ts)

    if state.first_sentence_ts is None and contains_complete_sentence(state.final_text):
        state.first_sentence_ts = time.perf_counter()
        metrics["time_to_first_complete_sentence_ms"] = _ms_since_sent(state, state.first_sentence_ts)

    state.chunks += 1
    return metrics


def finalize_metrics(state: StreamState, cancelled: bool = False) -> dict[str, Any]:
    """Build the final metrics dict after streaming completes."""
    done_ts = time.perf_counter()
    ttfb_ms = _ms_since_sent(state, state.first_token_ts)
    stream_ms = None
    if state.first_token_ts is not None:
        stream_ms = (done_ts - state.first_token_ts) * 1000.0
    total_ms = (done_ts - state.sent_ts) * 1000.0
    return {
        "ok": not cancelled,
        "ttfb_ms": round_ms(ttfb_ms),
        "ttfb_chat_ms": round_ms(ttfb_ms),
        "ttfb_toolcall_ms": round_ms(state.toolcall_ttfb_ms),
        "total_ms": round_ms(total_ms),
        "stream_ms": round_ms(stream_ms),
        "time_to_first_complete_sentence_ms": round_ms(_ms_since_sent(state, state.first_sentence_ts)),
        "time_to_first_3_words_ms": round_ms(_ms_since_sent(state, state.first_3_words_ts)),
        "chunks": state.chunks,
        "chars": len(state.final_text),
    }


# ============================================================================
# Stream Consumption
# ============================================================================


async def consume_stream(ws, state: StreamState) -> str:
    """Consume streaming response until done message, tracking metrics."""
    async for msg in iter_messages(ws):
        msg_type = msg.get("type")

        if msg_type == "toolcall":
            record_toolcall(state)
            continue

        if msg_type == "token":
            record_token(state, msg.get("text", ""))
            continue

        if msg_type == "final":
            normalized = msg.get("normalized_text")
            if normalized:
                state.final_text = normalized
            continue

        if msg_type == "done":
            return state.final_text

        if msg_type == "error":
            raise StreamError(msg)

    raise RuntimeError("WebSocket closed before receiving 'done'")


__all__ = [
    "create_tracker",
    "record_toolcall",
    "record_token",
    "finalize_metrics",
    "consume_stream",
]

