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
    green,
    yellow,
)
from tests.helpers.message import iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.stream import (
    consume_stream,
    create_tracker,
    finalize_metrics,
    StreamError,
)
from tests.helpers.ttfb import (
    create_ttfb_aggregator,
    emit_ttfb_summary,
    has_ttfb_samples,
    record_ttfb,
)
from tests.helpers.types import StreamState, TTFBSamples
from tests.helpers.ws import send_client_end, with_api_key
from tests.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES


# ============================================================================
# Internal Helpers
# ============================================================================


async def _wait_for_ack(ws) -> dict[str, Any] | None:
    """Wait for ack message and return history info if present."""
    async for msg in iter_messages(ws):
        if msg.get("type") == "ack":
            return msg.get("history")
        if msg.get("type") == "error":
            raise ServerError.from_message(msg)
    return None


async def _collect_response(ws, state: StreamState) -> str:
    """Collect streaming response until done message, tracking metrics."""
    try:
        return await consume_stream(ws, state)
    except StreamError as exc:
        raise ServerError.from_message(exc.message) from exc


def _build_start_payload(
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    history: list[dict[str, str]],
    user_text: str,
    sampling: dict[str, float | int] | None,
) -> dict[str, Any]:
    """Build the start message payload."""
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
    return payload


def _print_exchange(
    idx: int,
    user_text: str,
    reply: str,
    metrics: dict[str, Any],
) -> None:
    """Print a formatted exchange."""
    print(exchange_header(idx=idx))
    print(f"  {format_user(user_text)}")
    print(f"  {format_assistant(reply)}")
    print(f"  {format_metrics_inline(metrics)}")
    print(exchange_footer())


async def _send_start_request(
    ws,
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    history: list[dict[str, str]],
    user_text: str,
    sampling: dict[str, float | int] | None,
    ttfb_samples: TTFBSamples,
    idx: int,
) -> tuple[str, dict[str, Any]]:
    """Send a start request and collect the response with metrics tracking."""
    payload = _build_start_payload(
        session_id, gender, personality, chat_prompt, history, user_text, sampling
    )

    state = create_tracker()
    await ws.send(json.dumps(payload))
    await _wait_for_ack(ws)
    reply = await _collect_response(ws, state)
    metrics = finalize_metrics(state)

    _print_exchange(idx, user_text, reply, metrics)
    record_ttfb(ttfb_samples, metrics)
    return reply, metrics


def _format_history_kept(history_info: dict[str, Any]) -> str:
    """Format the 'history kept' line for display."""
    retained = history_info.get("retained_turns", 0)
    tokens = history_info.get("history_tokens", 0)
    trimmed = history_info.get("trimmed", False)
    
    status = yellow("trimmed") if trimmed else green("retained")
    return f"{retained} turns, {tokens} tokens ({status})"


def _print_header(
    personality: str,
    gender: str,
    history_info: dict[str, Any] | None,
) -> None:
    """Print the test header with history info."""
    print(f"\n{section_header('HISTORY RECALL TEST')}")
    if history_info:
        input_msgs = history_info.get("input_messages", 0)
        retained = history_info.get("retained_turns", 0)
        print(dim(f"  history in:   {input_msgs} msgs → {retained} turns"))
        print(dim(f"  history kept: {_format_history_kept(history_info)}"))
    else:
        print(dim(f"  warm history: {len(WARM_HISTORY)} messages"))
    print(dim(f"  recall tests: {len(HISTORY_RECALL_MESSAGES)} messages"))
    print(dim(f"  persona: {personality}/{gender}\n"))


async def _run_history_sequence(
    ws,
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    sampling: dict[str, float | int] | None,
    ttfb_samples: TTFBSamples,
) -> None:
    """Run through all history recall messages."""
    history: list[dict[str, str]] = list(WARM_HISTORY)
    
    first_user_text = HISTORY_RECALL_MESSAGES[0]
    payload = _build_start_payload(
        session_id, gender, personality, chat_prompt, history, first_user_text, sampling
    )
    
    state = create_tracker()
    await ws.send(json.dumps(payload))
    history_info = await _wait_for_ack(ws)
    
    _print_header(personality, gender, history_info)
    
    reply = await _collect_response(ws, state)
    metrics = finalize_metrics(state)
    _print_exchange(1, first_user_text, reply, metrics)
    record_ttfb(ttfb_samples, metrics)
    
    history.append({"role": "user", "content": first_user_text})
    history.append({"role": "assistant", "content": reply})

    for idx, user_text in enumerate(HISTORY_RECALL_MESSAGES[1:], 2):
        reply, _ = await _send_start_request(
            ws,
            session_id,
            gender,
            personality,
            chat_prompt,
            history,
            user_text,
            sampling,
            ttfb_samples,
            idx,
        )
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
    ttfb_samples = create_ttfb_aggregator()
    session_id = f"history-{uuid.uuid4()}"
    chat_prompt = select_chat_prompt(gender)

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
                ttfb_samples,
            )
        finally:
            await send_client_end(ws)

    print()
    if has_ttfb_samples(ttfb_samples):
        emit_ttfb_summary(ttfb_samples, print)
    else:
        print(dim("No TTFB samples collected"))


__all__ = ["run_test"]
