"""Test sequence orchestration for personality switch tests."""

from __future__ import annotations

import os
import sys

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from common.rate import SlidingWindowPacer
from config import PERSONALITY_NAME_CHECK_PROMPT, PERSONALITY_REPLIES_PER_SWITCH

from .messaging import send_persona_update, send_user_exchange
from .session import PersonaSession, PersonaVariant


async def run_initial_exchange(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    """Run the initial exchange with the first persona."""
    opener = session.next_script_prompt()
    await send_user_exchange(
        ws,
        session,
        variant,
        opener,
        message_pacer=message_pacer,
    )


async def run_switch_sequence(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    persona_pacer: SlidingWindowPacer | None = None,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    """Run a persona switch sequence: update persona, check name, then continue prompts."""
    if not session.has_remaining_prompts():
        return
    await send_persona_update(
        ws,
        session,
        variant,
        persona_pacer=persona_pacer,
        message_pacer=message_pacer,
    )
    await send_user_exchange(
        ws,
        session,
        variant,
        PERSONALITY_NAME_CHECK_PROMPT,
        message_pacer=message_pacer,
    )
    for _ in range(PERSONALITY_REPLIES_PER_SWITCH):
        if not session.has_remaining_prompts():
            break
        user_text = session.next_script_prompt()
        await send_user_exchange(
            ws,
            session,
            variant,
            user_text,
            message_pacer=message_pacer,
        )


async def run_remaining_sequence(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    """Run through any remaining prompts with the current persona."""
    while session.has_remaining_prompts():
        user_text = session.next_script_prompt()
        await send_user_exchange(
            ws,
            session,
            variant,
            user_text,
            message_pacer=message_pacer,
        )


