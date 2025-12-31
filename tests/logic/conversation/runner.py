"""Conversation history test runner.

This module orchestrates multi-turn conversation tests over WebSocket. It
maintains session state, tracks TTFB metrics across exchanges, and validates
that history retention works correctly under bounded-history constraints.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Sequence

import websockets  # type: ignore[import-not-found]

from tests.config import (
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
)
from tests.helpers.env import get_float_env, get_int_env
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.stream import StreamTracker
from tests.helpers.ttfb import TTFBAggregator
from tests.helpers.ws import send_client_end, with_api_key

from .session import ConversationSession, build_start_payload
from .stream import stream_exchange

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
    """
    Execute a multi-turn conversation test.

    Connects to the WebSocket server and replays the given prompts, tracking
    TTFB and other metrics for each exchange.
    """
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

    logger.info("Connecting to %s (session=%s)", ws_url, session.session_id)
    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    ttfb_aggregator = TTFBAggregator()

    async with websockets.connect(
        ws_url_with_auth,
        max_queue=None,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            for idx, user_text in enumerate(prompts, start=1):
                tracker = StreamTracker()
                payload = build_start_payload(session, user_text)
                logger.info("---- Exchange %02d ----", idx)
                logger.info("User → %r", user_text)
                await message_pacer.wait_turn()
                await ws.send(json.dumps(payload))
                assistant_text, metrics = await stream_exchange(ws, tracker, recv_timeout, idx)
                session.append_exchange(user_text, assistant_text)
                ttfb_aggregator.record(metrics)
                logger.info("Assistant ← %s", assistant_text)
        finally:
            if ttfb_aggregator.has_samples():
                ttfb_aggregator.emit(logger.info)
            await send_client_end(ws)


__all__ = ["run_conversation"]
