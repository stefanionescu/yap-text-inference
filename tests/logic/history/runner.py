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
from tests.helpers.fmt import (
    section_header,
    exchange_header,
    exchange_footer,
    format_user,
    format_assistant,
    format_metrics_inline,
    dim,
)
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
            tracker.record_toolcall()
            continue

        if t == "token":
            chunk = msg.get("text", "")
            tracker.record_token(chunk)
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
    idx: int,
    total: int,
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

    # Clean formatted output
    print(exchange_header(idx=idx))
    print(f"  {format_user(user_text)}")
    print(f"  {format_assistant(reply)}")
    print(f"  {format_metrics_inline(metrics)}")
    print(exchange_footer())

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
    total = len(HISTORY_RECALL_MESSAGES)

    for idx, user_text in enumerate(HISTORY_RECALL_MESSAGES, 1):
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
            idx,
            total,
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

    print(f"\n{section_header('HISTORY RECALL TEST')}")
    print(dim(f"  warm history: {len(WARM_HISTORY)} messages"))
    print(dim(f"  recall tests: {len(HISTORY_RECALL_MESSAGES)} messages"))
    print(dim(f"  persona: {personality}/{gender}\n"))

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

    print()
    if ttfb_aggregator.has_samples():
        ttfb_aggregator.emit(print)
    else:
        print(dim("No TTFB samples collected"))


__all__ = ["run_test"]
