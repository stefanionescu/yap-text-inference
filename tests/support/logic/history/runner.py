"""Main test runner for history recall tests.

Connects to the server with a pre-built conversation history, then sends
follow-up messages to test the assistant's recall of earlier exchanges.
Tracks TTFB for each response and prints summary statistics.
"""

from __future__ import annotations

import json
import uuid
import websockets
from typing import Any
from tests.support.helpers.prompt import select_chat_prompt
from tests.support.helpers.errors import ServerError, StreamError
from tests.config import DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.support.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES
from tests.state import StreamState, TTFBSamples, SessionContext, StartPayloadMode
from tests.support.helpers.metrics import record_ttfb, has_ttfb_samples, emit_ttfb_summary, create_ttfb_aggregator
from tests.support.helpers.fmt import (
    dim,
    format_user,
    section_header,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_metrics_inline,
)
from tests.support.helpers.websocket import (
    with_api_key,
    consume_stream,
    create_tracker,
    send_client_end,
    finalize_metrics,
    build_start_payload,
    build_api_key_headers,
    build_message_payload,
    includes_chat_start_fields,
)

# ============================================================================
# Internal Helpers
# ============================================================================


async def _collect_response(ws, state: StreamState) -> str:
    """Collect streaming response until done message, tracking metrics."""
    try:
        return await consume_stream(ws, state)
    except StreamError as exc:
        raise ServerError.from_message(exc.message) from exc


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


async def _send_message_request(
    ws,
    ctx: SessionContext,
    user_text: str,
    ttfb_samples: TTFBSamples,
    idx: int,
) -> tuple[str, dict[str, Any]]:
    """Send a message request and collect the response with metrics tracking."""
    payload = build_message_payload(user_text, sampling=ctx.sampling)

    state = create_tracker()
    await ws.send(json.dumps(payload))
    reply = await _collect_response(ws, state)
    metrics = finalize_metrics(state)

    _print_exchange(idx, user_text, reply, metrics)
    record_ttfb(ttfb_samples, metrics)
    return reply, metrics


def _print_header(
    personality: str,
    gender: str,
) -> None:
    """Print the test header."""
    print(f"\n{section_header('HISTORY RECALL TEST')}")
    print(dim(f"  warm history: {len(WARM_HISTORY)} messages"))
    print(dim(f"  recall tests: {len(HISTORY_RECALL_MESSAGES)} messages"))
    print(dim(f"  persona: {personality}/{gender}\n"))


async def _run_history_sequence(
    ws,
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str | None,
    sampling: dict[str, float | int] | None,
    ttfb_samples: TTFBSamples,
    start_payload_mode: StartPayloadMode,
) -> None:
    """Run through all history recall messages."""
    history: list[dict[str, str]] = list(WARM_HISTORY)
    ctx = SessionContext(
        session_id=session_id,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        sampling=sampling,
        start_payload_mode=start_payload_mode,
    )

    first_user_text = HISTORY_RECALL_MESSAGES[0]
    payload = build_start_payload(ctx, first_user_text, history=history)

    state = create_tracker()
    await ws.send(json.dumps(payload))

    _print_header(personality, gender)

    reply = await _collect_response(ws, state)
    metrics = finalize_metrics(state)
    _print_exchange(1, first_user_text, reply, metrics)
    record_ttfb(ttfb_samples, metrics)

    for idx, user_text in enumerate(HISTORY_RECALL_MESSAGES[1:], 2):
        reply, _ = await _send_message_request(
            ws,
            ctx,
            user_text,
            ttfb_samples,
            idx,
        )


# ============================================================================
# Public API
# ============================================================================


async def run_test(
    ws_url: str,
    api_key: str | None,
    gender: str,
    personality: str,
    sampling: dict[str, float | int] | None,
    start_payload_mode: StartPayloadMode = "all",
) -> None:
    """Run the history recall test."""
    url = with_api_key(ws_url, api_key=api_key)
    ws_headers = build_api_key_headers(api_key=api_key)
    ttfb_samples = create_ttfb_aggregator()
    session_id = f"history-{uuid.uuid4()}"
    chat_prompt = select_chat_prompt(gender) if includes_chat_start_fields(start_payload_mode) else None

    async with websockets.connect(
        url,
        additional_headers=ws_headers,
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
                start_payload_mode,
            )
        finally:
            await send_client_end(ws)

    print()
    if has_ttfb_samples(ttfb_samples):
        emit_ttfb_summary(ttfb_samples, print)
    else:
        print(dim("No TTFB samples collected"))


__all__ = ["run_test"]
