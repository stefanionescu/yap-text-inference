"""WebSocket message handling for gender tests."""

from __future__ import annotations

import json
from typing import Any

from tests.config import DEFAULT_PERSONALITIES
from tests.helpers.errors import ServerError
from tests.helpers.fmt import (
    exchange_header,
    exchange_footer,
    format_user,
    format_assistant,
    format_metrics_inline,
)
from tests.helpers.message import iter_messages
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.stream import StreamTracker

from .session import PersonaSession, PersonaVariant


async def collect_response(ws, tracker: StreamTracker) -> str:
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
        "personalities": DEFAULT_PERSONALITIES,
        "chat_prompt": variant.chat_prompt,
        "history": session.history,
        "user_utterance": user_text,
    }
    if session.sampling:
        payload["sampling"] = session.sampling
    if message_pacer:
        await message_pacer.wait_turn()

    tracker = StreamTracker()
    await ws.send(json.dumps(payload))
    reply = await collect_response(ws, tracker)
    metrics = tracker.finalize_metrics()
    
    # Clean formatted output
    print(exchange_header(persona=variant.personality, gender=variant.gender))
    print(f"  {format_user(user_text)}")
    print(f"  {format_assistant(reply)}")
    print(f"  {format_metrics_inline(metrics)}")
    print(exchange_footer())
    
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

