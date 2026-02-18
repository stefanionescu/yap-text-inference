"""Conversation history test runner.

This module orchestrates multi-turn conversation tests over WebSocket. It
maintains session state, tracks TTFB metrics across exchanges, and validates
that history retention works correctly under bounded-history constraints.
"""

from __future__ import annotations

import json
import uuid
import logging
from collections.abc import Sequence

import websockets

from tests.state import ConversationSession
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.env import get_int_env, get_float_env
from tests.helpers.websocket import with_api_key, create_tracker, send_client_end
from tests.helpers.metrics import record_ttfb, has_ttfb_samples, emit_ttfb_summary, create_ttfb_aggregator
from tests.config import DEFAULT_GENDER, DEFAULT_PERSONALITY, DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.helpers.fmt import (
    dim,
    format_user,
    section_header,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_metrics_inline,
)

from .stream import stream_exchange
from .session import build_start_payload, build_message_payload

logger = logging.getLogger(__name__)

MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


async def run_conversation(
    ws_url: str,
    api_key: str | None,
    prompts: Sequence[str],
    gender: str,
    personality: str,
    recv_timeout: float,
    sampling: dict[str, float | int] | None,
) -> None:
    """Execute a multi-turn conversation test."""
    if not prompts:
        raise ValueError("Conversation prompt list is empty; nothing to send.")

    gender = gender or DEFAULT_GENDER
    personality = personality or DEFAULT_PERSONALITY

    ws_url_with_auth = with_api_key(ws_url, api_key=api_key)
    chat_prompt = select_chat_prompt(gender)
    session = ConversationSession(
        session_id=f"sess-{uuid.uuid4()}",
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        sampling=sampling,
    )

    print(f"\n{section_header('CONVERSATION TEST')}")
    print(dim(f"  session: {session.session_id}"))
    print(dim(f"  persona: {personality}/{gender}\n"))

    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    ttfb_samples = create_ttfb_aggregator()

    async with websockets.connect(
        ws_url_with_auth,
        max_queue=None,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            for idx, user_text in enumerate(prompts, start=1):
                state = create_tracker()
                payload = (
                    build_start_payload(session, user_text) if idx == 1 else build_message_payload(session, user_text)
                )

                print(exchange_header(idx=idx))
                print(f"  {format_user(user_text)}")

                await message_pacer.wait_turn()
                await ws.send(json.dumps(payload))
                assistant_text, metrics = await stream_exchange(ws, state, recv_timeout, idx)
                record_ttfb(ttfb_samples, metrics)

                print(f"  {format_assistant(assistant_text)}")
                print(f"  {format_metrics_inline(metrics)}")
                print(exchange_footer())
        finally:
            print()
            if has_ttfb_samples(ttfb_samples):
                emit_ttfb_summary(ttfb_samples, print)
            await send_client_end(ws, session.session_id)


__all__ = ["run_conversation"]
