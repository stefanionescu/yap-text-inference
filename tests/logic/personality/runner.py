"""Main test runner for personality switch tests."""

from __future__ import annotations

import asyncio
import uuid

import websockets  # type: ignore[import-not-found]

from tests.config import (
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    PERSONALITY_PERSONA_VARIANTS,
)
from tests.helpers.env import get_float_env, get_int_env
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.ttfb import TTFBAggregator
from tests.helpers.ws import send_client_end, with_api_key
from tests.messages.personality import PERSONALITY_CONVERSATION_MESSAGES

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
    ttfb_aggregator = TTFBAggregator()
    session = _build_session(sampling)
    session.ttfb_aggregator = ttfb_aggregator
    variants = _load_variants()
    message_pacer, persona_pacer = _build_pacers()
    try:
        await _execute_test(url, session, variants, switches, delay_s, message_pacer, persona_pacer)
    finally:
        if ttfb_aggregator.has_samples():
            ttfb_aggregator.emit(print)


def _build_session(
    sampling: dict[str, float | int] | None,
) -> PersonaSession:
    prompt_sequence = tuple(PERSONALITY_CONVERSATION_MESSAGES)
    if not prompt_sequence:
        raise RuntimeError("PERSONALITY_CONVERSATION_MESSAGES is empty; nothing to test.")
    return PersonaSession(
        session_id=f"sess-{uuid.uuid4()}",
        prompts=prompt_sequence,
        sampling=sampling,
    )


def _load_variants() -> list[PersonaVariant]:
    variants: list[PersonaVariant] = [PersonaVariant(*variant) for variant in PERSONALITY_PERSONA_VARIANTS]
    if not variants:
        raise RuntimeError("PERSONALITY_PERSONA_VARIANTS is empty; nothing to test.")
    return variants


def _build_pacers() -> tuple[SlidingWindowPacer, SlidingWindowPacer]:
    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    persona_pacer = SlidingWindowPacer(PERSONA_MAX_PER_WINDOW, PERSONA_WINDOW_SECONDS)
    return message_pacer, persona_pacer


async def _execute_test(
    url: str,
    session: PersonaSession,
    variants: list[PersonaVariant],
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> None:
    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            await _run_sequences(ws, session, variants, switches, delay_s, message_pacer, persona_pacer)
        finally:
            await send_client_end(ws)


async def _run_sequences(
    ws,
    session: PersonaSession,
    variants: list[PersonaVariant],
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> None:
    current_idx = 0
    await run_initial_exchange(
        ws,
        session,
        variants[current_idx],
        message_pacer=message_pacer,
    )
    current_idx = await _perform_switches(
        ws,
        session,
        variants,
        current_idx,
        switches,
        delay_s,
        message_pacer,
        persona_pacer,
    )
    if session.has_remaining_prompts():
        await run_remaining_sequence(
            ws,
            session,
            variants[current_idx],
            message_pacer=message_pacer,
        )


async def _perform_switches(
    ws,
    session: PersonaSession,
    variants: list[PersonaVariant],
    current_idx: int,
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> int:
    for _ in range(switches):
        if not session.has_remaining_prompts():
            break
        await asyncio.sleep(delay_s)
        current_idx = (current_idx + 1) % len(variants)
        await run_switch_sequence(
            ws,
            session,
            variants[current_idx],
            persona_pacer=persona_pacer,
            message_pacer=message_pacer,
        )
    return current_idx

