"""Main test runner for personality switch tests."""

from __future__ import annotations

import asyncio
import os
import sys
import uuid

import websockets  # type: ignore[import-not-found]

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.ws import send_client_end, with_api_key
from tests.config import (
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    PERSONA_VARIANTS,
)
from tests.messages.conversation import CONVERSATION_HISTORY_MESSAGES
from tests.config.env import get_float_env, get_int_env

from .sequences import run_initial_exchange, run_remaining_sequence, run_switch_sequence
from .session import PersonaSession, PersonaVariant

PERSONA_WINDOW_SECONDS = get_float_env("CHAT_PROMPT_UPDATE_WINDOW_SECONDS", 60.0)
PERSONA_MAX_PER_WINDOW = get_int_env("CHAT_PROMPT_UPDATE_MAX_PER_WINDOW", 4)
MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


async def run_test(
    ws_url: str,
    api_key: str | None,
    switches: int,
    delay_s: int,
    sampling: dict[str, float | int] | None,
) -> None:
    """Run the personality switch test."""
    url = with_api_key(ws_url, api_key=api_key)
    prompt_sequence = tuple(CONVERSATION_HISTORY_MESSAGES)
    if not prompt_sequence:
        raise RuntimeError("CONVERSATION_HISTORY_MESSAGES is empty; nothing to test.")
    session = PersonaSession(
        session_id=f"sess-{uuid.uuid4()}",
        prompts=prompt_sequence,
        sampling=sampling,
    )
    variants: list[PersonaVariant] = [PersonaVariant(*variant) for variant in PERSONA_VARIANTS]
    if not variants:
        raise RuntimeError("PERSONA_VARIANTS is empty; nothing to test.")

    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    persona_pacer = SlidingWindowPacer(PERSONA_MAX_PER_WINDOW, PERSONA_WINDOW_SECONDS)

    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            current_variant_idx = 0
            await run_initial_exchange(
                ws,
                session,
                variants[current_variant_idx],
                message_pacer=message_pacer,
            )
            for _ in range(switches):
                if not session.has_remaining_prompts():
                    break
                await asyncio.sleep(delay_s)
                current_variant_idx = (current_variant_idx + 1) % len(variants)
                variant = variants[current_variant_idx]
                await run_switch_sequence(
                    ws,
                    session,
                    variant,
                    persona_pacer=persona_pacer,
                    message_pacer=message_pacer,
                )
            if session.has_remaining_prompts():
                await run_remaining_sequence(
                    ws,
                    session,
                    variants[current_variant_idx],
                    message_pacer=message_pacer,
                )
        finally:
            await send_client_end(ws)


