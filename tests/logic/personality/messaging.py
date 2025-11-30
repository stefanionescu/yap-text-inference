"""WebSocket message handling for personality tests."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.helpers.message import iter_messages
from tests.helpers.rate import SlidingWindowPacer
from .session import PersonaSession, PersonaVariant
from .tracker import StreamTracker


async def collect_response(ws, tracker: StreamTracker) -> str:
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
            if metrics.get("ttfb_chat_ms") is not None:
                print(f"  [chat] ttfb_ms={metrics['ttfb_chat_ms']:.2f}")
            if metrics.get("first_3_words_ms") is not None:
                print(f"  [chat] first_3_words_ms={metrics['first_3_words_ms']:.2f}")
            if metrics.get("first_sentence_ms") is not None:
                print(f"  [chat] first_sentence_ms={metrics['first_sentence_ms']:.2f}")
            continue

        if t == "final":
            if msg.get("normalized_text"):
                tracker.final_text = msg["normalized_text"]
            continue

        if t == "done":
            return tracker.final_text

        if t == "error":
            raise RuntimeError(f"server error: {msg}")

    raise RuntimeError("WebSocket closed before receiving 'done'")


async def send_start_request(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    user_text: str,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> tuple[str, dict[str, Any]]:
    """Send a start request and collect the response with metrics tracking."""
    payload = {
        "type": "start",
        "session_id": session.session_id,
        "gender": variant.gender,
        "personality": variant.personality,
        "chat_prompt": variant.chat_prompt,
        "history_text": session.history,
        "user_utterance": user_text,
    }
    if session.tool_prompt is not None:
        payload["tool_prompt"] = session.tool_prompt
    if session.sampling:
        payload["sampling"] = session.sampling
    if message_pacer:
        await message_pacer.wait_turn()

    tracker = StreamTracker()
    await ws.send(json.dumps(payload))
    reply = await collect_response(ws, tracker)
    metrics = tracker.finalize_metrics()
    print(
        f"[persona={variant.personality} gender={variant.gender}] "
        f"user: {user_text!r}"
    )
    print(f"  -> assistant: {reply!r}")
    print(f"  -> metrics: {json.dumps(metrics)}")
    return reply, metrics


async def wait_for_chat_prompt_ack(ws) -> dict:
    """Wait for chat_prompt acknowledgement message."""
    async for msg in iter_messages(ws):
        if msg.get("type") == "ack" and msg.get("for") == "chat_prompt":
            return msg
        if msg.get("type") == "error":
            return msg
    raise RuntimeError("WebSocket closed before receiving chat_prompt ack")


async def send_persona_update(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    persona_pacer: SlidingWindowPacer | None = None,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    """Send a persona/chat_prompt update to the server."""
    payload = {
        "type": "chat_prompt",
        "session_id": session.session_id,
        "gender": variant.gender,
        "personality": variant.personality,
        "chat_prompt": variant.chat_prompt,
        "history_text": session.history,
    }
    if persona_pacer:
        await persona_pacer.wait_turn()
    if message_pacer:
        await message_pacer.wait_turn()
    await ws.send(json.dumps(payload))
    ack = await wait_for_chat_prompt_ack(ws)
    if not (ack.get("type") == "ack" and ack.get("ok") and ack.get("code") in (200, 204)):
        raise RuntimeError(f"update_chat_prompt failed: {ack}")


async def send_user_exchange(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    user_text: str,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    """Send a user message and append the exchange to session history."""
    assistant_text, metrics = await send_start_request(
        ws,
        session,
        variant,
        user_text,
        message_pacer=message_pacer,
    )
    session.append_exchange(user_text, assistant_text)
    if session.ttfb_aggregator is not None:
        session.ttfb_aggregator.record(metrics)

