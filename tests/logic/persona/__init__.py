"""Shared logic for persona/gender switch tests.

This module provides common infrastructure for tests that switch between
personas mid-session. Used by both gender tests (switching gender with same
personality) and personality tests (switching personality across genders).
"""

from .messaging import (
    collect_response,
    send_persona_update,
    send_start_request,
    send_user_exchange,
    wait_for_chat_prompt_ack,
)
from .runner import run_persona_test
from .sequences import (
    run_initial_exchange,
    run_remaining_sequence,
    run_switch_sequence,
)
from .session import PersonaSession, PersonaVariant
from .types import PersonaSwitchConfig

__all__ = [
    # messaging
    "collect_response",
    "send_persona_update",
    "send_start_request",
    "send_user_exchange",
    "wait_for_chat_prompt_ack",
    # runner
    "run_persona_test",
    # sequences
    "run_initial_exchange",
    "run_remaining_sequence",
    "run_switch_sequence",
    # session
    "PersonaSession",
    "PersonaVariant",
    # types
    "PersonaSwitchConfig",
]

