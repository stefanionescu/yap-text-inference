from __future__ import annotations

try:  # When /test is already on sys.path
    from prompts.chat import FIRST_PROMPT, SECOND_PROMPT
except ModuleNotFoundError:  # When repo root is on sys.path
    from test.prompts.chat import FIRST_PROMPT, SECOND_PROMPT

__all__ = ["normalize_gender", "select_chat_prompt"]


def normalize_gender(value: str | None) -> str:
    """Normalize assistant gender strings to canonical lowercase tokens."""
    if not value:
        return ""
    return value.strip().lower()


def select_chat_prompt(gender: str | None) -> str:
    """
    Choose an appropriate chat prompt template based on assistant gender.

    Defaults to the SECOND_PROMPT (Mark) when the provided gender does not
    normalize to "female".
    """
    normalized = normalize_gender(gender)
    return FIRST_PROMPT if normalized == "female" else SECOND_PROMPT


