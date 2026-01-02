"""Configuration types for persona switch tests.

This module defines the configuration dataclass used to parameterize
persona switch tests, allowing the same logic to drive both gender
and personality switch test variants.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaSwitchConfig:
    """Configuration for a persona switch test run.
    
    Attributes:
        test_name: Display name for the test (e.g., "GENDER SWITCH TEST").
        prompts: Sequence of user prompts to send during the test.
        name_check_message: Message sent after each switch to verify persona.
        variants: List of (gender, personality, chat_prompt) tuples.
        replies_per_switch: Number of follow-up messages after each switch.
    """

    test_name: str
    prompts: Sequence[str]
    name_check_message: str
    variants: Sequence[tuple[str, str, str]]
    replies_per_switch: int


__all__ = ["PersonaSwitchConfig"]

