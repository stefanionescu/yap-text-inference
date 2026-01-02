"""Main test runner for persona switch tests.

This module provides the unified runner for both gender and personality
switch tests. It handles connection setup, session management, switch
sequencing, and metrics aggregation.
"""

from __future__ import annotations

import asyncio
import uuid

import websockets  # type: ignore[import-not-found]

from tests.config import DEFAULT_WS_PING_INTERVAL, DEFAULT_WS_PING_TIMEOUT
from tests.helpers.env import get_float_env, get_int_env
from tests.helpers.fmt import section_header, dim
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.ttfb import (
    create_ttfb_aggregator,
    emit_ttfb_summary,
    has_ttfb_samples,
)
from tests.helpers.ws import send_client_end, with_api_key

from .sequences import run_initial_exchange, run_remaining_sequence, run_switch_sequence
from .session import PersonaSession, PersonaVariant
from .types import PersonaSwitchConfig


# ============================================================================
# Configuration
# ============================================================================


PERSONA_WINDOW_SECONDS = get_float_env("CHAT_PROMPT_UPDATE_WINDOW_SECONDS", 60.0)
PERSONA_MAX_PER_WINDOW = get_int_env("CHAT_PROMPT_UPDATE_MAX_PER_WINDOW", 4)
MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


# ============================================================================
# Internal Helpers
# ============================================================================


def _build_session(
    prompts: tuple[str, ...],
    sampling: dict[str, float | int] | None,
) -> PersonaSession:
    """Build a new persona session with the given prompts."""
    if not prompts:
        raise RuntimeError("Prompts sequence is empty; nothing to test.")
    return PersonaSession(
        session_id=f"sess-{uuid.uuid4()}",
        prompts=prompts,
        sampling=sampling,
    )


def _load_variants(raw_variants: tuple[tuple[str, str, str], ...]) -> list[PersonaVariant]:
    """Convert raw variant tuples to PersonaVariant objects."""
    variants = [PersonaVariant(*variant) for variant in raw_variants]
    if not variants:
        raise RuntimeError("Variants list is empty; nothing to test.")
    return variants


def _build_pacers() -> tuple[SlidingWindowPacer, SlidingWindowPacer]:
    """Create rate limiters for messages and persona updates."""
    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    persona_pacer = SlidingWindowPacer(PERSONA_MAX_PER_WINDOW, PERSONA_WINDOW_SECONDS)
    return message_pacer, persona_pacer


async def _execute_test(
    url: str,
    session: PersonaSession,
    variants: list[PersonaVariant],
    config: PersonaSwitchConfig,
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> None:
    """Execute the test over a WebSocket connection."""
    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            await _run_sequences(
                ws, session, variants, config, switches, delay_s,
                message_pacer, persona_pacer
            )
        finally:
            await send_client_end(ws)


async def _run_sequences(
    ws,
    session: PersonaSession,
    variants: list[PersonaVariant],
    config: PersonaSwitchConfig,
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> None:
    """Run the full sequence of exchanges and switches."""
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
        config,
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
    config: PersonaSwitchConfig,
    current_idx: int,
    switches: int,
    delay_s: int,
    message_pacer: SlidingWindowPacer,
    persona_pacer: SlidingWindowPacer,
) -> int:
    """Perform the configured number of persona switches."""
    for _ in range(switches):
        if not session.has_remaining_prompts():
            break
        await asyncio.sleep(delay_s)
        current_idx = (current_idx + 1) % len(variants)
        await run_switch_sequence(
            ws,
            session,
            variants[current_idx],
            config.name_check_message,
            config.replies_per_switch,
            persona_pacer=persona_pacer,
            message_pacer=message_pacer,
        )
    return current_idx


# ============================================================================
# Public API
# ============================================================================


async def run_persona_test(
    ws_url: str,
    api_key: str | None,
    config: PersonaSwitchConfig,
    switches: int,
    delay_s: int,
    sampling: dict[str, float | int] | None,
) -> None:
    """Run a persona switch test with the given configuration."""
    url = with_api_key(ws_url, api_key=api_key)
    
    print(f"\n{section_header(config.test_name)}")
    print(dim(f"  switches: {switches}, delay: {delay_s}s\n"))
    
    ttfb_samples = create_ttfb_aggregator()
    prompts = tuple(config.prompts)
    variants_tuple = tuple(config.variants)
    
    session = _build_session(prompts, sampling)
    session.ttfb_samples = ttfb_samples
    variants = _load_variants(variants_tuple)
    message_pacer, persona_pacer = _build_pacers()
    
    try:
        await _execute_test(
            url, session, variants, config, switches, delay_s,
            message_pacer, persona_pacer
        )
    finally:
        print()
        if has_ttfb_samples(ttfb_samples):
            emit_ttfb_summary(ttfb_samples, print)


__all__ = ["run_persona_test"]
