from __future__ import annotations

try:  # When /tests is already on sys.path
    from prompts.chat import FEMALE_PROMPT, MALE_PROMPT
except ModuleNotFoundError:  # When repo root is on sys.path
    from tests.prompts.chat import FEMALE_PROMPT, MALE_PROMPT

__all__ = ["normalize_gender", "select_chat_prompt"]


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


