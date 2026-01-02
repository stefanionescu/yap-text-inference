"""Persona session and variant dataclasses for switch tests.

This module provides the session state management for persona switch tests,
tracking conversation history, prompt progression, and timing metrics.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from tests.helpers.types import TTFBSamples


@dataclass(frozen=True)
class PersonaVariant:
    """Immutable persona configuration."""

    gender: str
    personality: str
    chat_prompt: str


@dataclass
class PersonaSession:
    """Tracks session state, history, and prompt progression."""

    session_id: str
    prompts: Sequence[str]
    history: list[dict[str, str]] = field(default_factory=list)
    prompt_index: int = 0
    sampling: dict[str, float | int] | None = None
    ttfb_samples: TTFBSamples | None = None

    def has_remaining_prompts(self) -> bool:
        """Check if there are more prompts to process."""
        return self.prompt_index < len(self.prompts)

    def next_script_prompt(self) -> str:
        """Get the next prompt from the script and advance the index."""
        if not self.has_remaining_prompts():
            raise RuntimeError("No prompts remaining; cannot produce user prompt.")
        prompt = self.prompts[self.prompt_index]
        self.prompt_index += 1
        return prompt

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        """Append a user-assistant exchange to the history."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


__all__ = ["PersonaSession", "PersonaVariant"]
