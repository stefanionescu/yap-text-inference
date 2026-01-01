"""Main test runner for history recall tests.

Connects to the server with a pre-built conversation history, then sends
follow-up messages to test the assistant's recall of earlier exchanges.
Tracks TTFB for each response and prints summary statistics.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import websockets  # type: ignore[import-not-found]

from tests.config import (
    DEFAULT_PERSONALITIES,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from tests.helpers.errors import ServerError
from tests.helpers.message import iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.stream import StreamTracker
from tests.helpers.ttfb import TTFBAggregator
from tests.helpers.ws import send_client_end, with_api_key
from tests.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES


# ============================================================================
# Internal Helpers
# ============================================================================


async def _collect_response(ws, tracker: StreamTracker) -> str:
    """Collect streaming response until done message, tracking metrics."""
    async for msg in iter_messages(ws):
        t = msg.get("type")

        if t == "toolcall":
            ttfb = tracker.record_toolcall()
            status = msg.get("status")
            if ttfb is not None:
                print(f"  [toolcall] status={status} ttfb_ms={ttfb:.2f}")
            continue

        if t == "token":
            chunk = msg.get("text", "")
            metrics = tracker.record_token(chunk)
            if metrics.get("chat_ttfb_ms") is not None:
                print(f"  [chat] ttfb_ms={metrics['chat_ttfb_ms']:.2f}")
            if metrics.get("time_to_first_3_words_ms") is not None:
                print(f"  [chat] first_3_words_ms={metrics['time_to_first_3_words_ms']:.2f}")
            if metrics.get("time_to_first_complete_sentence_ms") is not None:
                print(f"  [chat] first_sentence_ms={metrics['time_to_first_complete_sentence_ms']:.2f}")
            continue

        if t == "final":
            if msg.get("normalized_text"):
                tracker.final_text = msg["normalized_text"]
            continue

        if t == "done":
            return tracker.final_text

        if t == "error":
            raise ServerError.from_message(msg)

    raise RuntimeError("WebSocket closed before receiving 'done'")


async def _send_start_request(
    ws,
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    history: list[dict[str, str]],
    user_text: str,
    sampling: dict[str, float | int] | None,
    ttfb_aggregator: TTFBAggregator,
) -> tuple[str, dict[str, Any]]:
    """Send a start request and collect the response with metrics tracking."""
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": personality,
        "personalities": DEFAULT_PERSONALITIES,
        "chat_prompt": chat_prompt,
        "history": history,
        "user_utterance": user_text,
    }
    if sampling:
        payload["sampling"] = sampling

    tracker = StreamTracker()
    await ws.send(json.dumps(payload))
    reply = await _collect_response(ws, tracker)
    metrics = tracker.finalize_metrics()

    print(f"[user] {user_text!r}")
    print(f"  -> assistant: {reply!r}")
    print(f"  -> metrics: {json.dumps(metrics)}")

    ttfb_aggregator.record(metrics)
    return reply, metrics


async def _run_history_sequence(
    ws,
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    sampling: dict[str, float | int] | None,
    ttfb_aggregator: TTFBAggregator,
) -> None:
    """Run through all history recall messages."""
    # Start with the pre-built history
    history: list[dict[str, str]] = list(WARM_HISTORY)

    print(f"\n{'='*60}")
    print(f"Starting history recall test with {len(history)} messages in history")
    print(f"Sending {len(HISTORY_RECALL_MESSAGES)} follow-up messages")
    print(f"{'='*60}\n")

    for idx, user_text in enumerate(HISTORY_RECALL_MESSAGES, 1):
        print(f"\n--- Message {idx}/{len(HISTORY_RECALL_MESSAGES)} ---")
        reply, _ = await _send_start_request(
            ws,
            session_id,
            gender,
            personality,
            chat_prompt,
            history,
            user_text,
            sampling,
            ttfb_aggregator,
        )
        # Append the exchange to history for subsequent messages
        history.append({"role": "user", "content": user_text})
        history.append({"role": "assistant", "content": reply})


# ============================================================================
# Public API
# ============================================================================


async def run_test(
    ws_url: str,
    api_key: str | None,
    gender: str,
    personality: str,
    sampling: dict[str, float | int] | None,
) -> None:
    """Run the history recall test."""
    url = with_api_key(ws_url, api_key=api_key)
    ttfb_aggregator = TTFBAggregator()
    session_id = f"history-{uuid.uuid4()}"
    chat_prompt = select_chat_prompt(gender)

    print(f"Connecting to {ws_url} (with API key auth)")
    print(f"Gender: {gender}, Personality: {personality}")

    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            await _run_history_sequence(
                ws,
                session_id,
                gender,
                personality,
                chat_prompt,
                sampling,
                ttfb_aggregator,
            )
        finally:
            await send_client_end(ws)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    if ttfb_aggregator.has_samples():
        ttfb_aggregator.emit(print)
    else:
        print("No TTFB samples collected")


__all__ = ["run_test"]
