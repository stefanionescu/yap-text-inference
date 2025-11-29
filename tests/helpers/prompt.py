from __future__ import annotations

from typing import Literal

try:  # When /tests is already on sys.path
    from tests.prompts.chat import FEMALE_PROMPT, MALE_PROMPT
    from tests.prompts.toolcall import DEFAULT_TOOL_PROMPT_NAME, TOOL_PROMPTS
except ModuleNotFoundError:  # When repo root is on sys.path
    from tests.prompts.chat import FEMALE_PROMPT, MALE_PROMPT
    from tests.prompts.toolcall import DEFAULT_TOOL_PROMPT_NAME, TOOL_PROMPTS

PromptMode = Literal["both", "chat", "tool"]

PROMPT_MODE_BOTH: PromptMode = "both"
PROMPT_MODE_CHAT_ONLY: PromptMode = "chat"
PROMPT_MODE_TOOL_ONLY: PromptMode = "tool"
PROMPT_MODE_CHOICES: tuple[PromptMode, ...] = (
    PROMPT_MODE_BOTH,
    PROMPT_MODE_CHAT_ONLY,
    PROMPT_MODE_TOOL_ONLY,
)

_TOOL_PROMPTS_BY_NAME: dict[str, str] = {
    (name or "").strip().lower(): prompt
    for name, prompt in TOOL_PROMPTS.items()
    if isinstance(prompt, str) and (name or "").strip()
}


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


def select_tool_prompt(name: str | None = None) -> str:
    """
    Look up a tool prompt by name (defaults to DEFAULT_TOOL_PROMPT_NAME).
    """

    lookup = normalize_tool_prompt_name(name)
    try:
        return _TOOL_PROMPTS_BY_NAME[lookup]
    except KeyError as exc:  # pragma: no cover - defensive guard
        available = ", ".join(sorted(_TOOL_PROMPTS_BY_NAME)) or "<none>"
        raise ValueError(f"unknown tool prompt '{name}'. Available: {available}") from exc


def normalize_tool_prompt_name(name: str | None) -> str:
    lookup = (name or DEFAULT_TOOL_PROMPT_NAME).strip().lower()
    if lookup not in _TOOL_PROMPTS_BY_NAME:
        available = ", ".join(sorted(_TOOL_PROMPTS_BY_NAME)) or "<none>"
        raise ValueError(f"unknown tool prompt '{name}'. Available: {available}")
    return lookup


def normalize_prompt_mode(value: str | None) -> PromptMode:
    """Normalize CLI/env prompt mode selections."""
    if not value:
        return PROMPT_MODE_BOTH
    lookup = value.strip().lower()
    if lookup not in PROMPT_MODE_CHOICES:
        allowed = ", ".join(PROMPT_MODE_CHOICES)
        raise ValueError(f"prompt mode must be one of {allowed}, got '{value}'")
    return lookup  # type: ignore[return-value]


def should_send_chat_prompt(mode: str | None) -> bool:
    normalized = normalize_prompt_mode(mode)
    return normalized in (PROMPT_MODE_BOTH, PROMPT_MODE_CHAT_ONLY)


def should_send_tool_prompt(mode: str | None) -> bool:
    normalized = normalize_prompt_mode(mode)
    return normalized in (PROMPT_MODE_BOTH, PROMPT_MODE_TOOL_ONLY)


__all__ = [
    "normalize_gender",
    "select_chat_prompt",
    "select_tool_prompt",
    "normalize_prompt_mode",
    "should_send_chat_prompt",
    "should_send_tool_prompt",
    "PROMPT_MODE_CHOICES",
    "PROMPT_MODE_BOTH",
    "PROMPT_MODE_CHAT_ONLY",
    "PROMPT_MODE_TOOL_ONLY",
]
