"""Prompt selection utilities for test utilities.

This module provides helpers for normalizing gender strings and selecting
appropriate chat prompts based on the assistant's gender. It imports the
base prompts from tests/prompts/base.py.
"""

from __future__ import annotations

try:  # When /tests is already on sys.path
    from tests.prompts.base import FEMALE_PROMPT, MALE_PROMPT
except ModuleNotFoundError:  # When repo root is on sys.path
    from tests.prompts.base import FEMALE_PROMPT, MALE_PROMPT


def normalize_gender(value: str | None) -> str:
    """Normalize assistant gender strings to canonical lowercase tokens."""
    if not value:
        return ""
    return value.strip().lower()


def select_chat_prompt(gender: str | None) -> str:
    """
    Choose an appropriate chat prompt template based on assistant gender.

    Defaults to the MALE_PROMPT (Mark) when the provided gender does not
    normalize to "female".
    """
    normalized = normalize_gender(gender)
    return FEMALE_PROMPT if normalized == "female" else MALE_PROMPT


__all__ = [
    "normalize_gender",
    "select_chat_prompt",
]
