"""Test sequence orchestration for persona switch tests.

This module provides the high-level sequence functions that coordinate
the flow of persona switch tests: initial exchange, switch sequences,
and remaining message completion.
"""

from __future__ import annotations

from tests.helpers.rate import SlidingWindowPacer

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
    name_check_message: str,
    replies_per_switch: int,
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
        name_check_message,
        message_pacer=message_pacer,
    )
    for _ in range(replies_per_switch):
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


__all__ = [
    "run_initial_exchange",
    "run_remaining_sequence",
    "run_switch_sequence",
]

