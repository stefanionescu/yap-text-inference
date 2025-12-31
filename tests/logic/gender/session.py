"""Persona session and variant dataclasses."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from tests.helpers.ttfb import TTFBAggregator
from tests.messages.conversation import CONVERSATION_HISTORY_MESSAGES


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
    history: str = ""
    prompt_index: int = 0
    prompts: Sequence[str] = field(default_factory=lambda: tuple(CONVERSATION_HISTORY_MESSAGES))
    sampling: dict[str, float | int] | None = None
    ttfb_aggregator: TTFBAggregator | None = None

    def has_remaining_prompts(self) -> bool:
        """Check if there are more prompts to process."""
        return self.prompt_index < len(self.prompts)

    def next_script_prompt(self) -> str:
        """Get the next prompt from the script and advance the index."""
        if not self.has_remaining_prompts():
            raise RuntimeError("CONVERSATION_HISTORY_MESSAGES is empty; cannot produce user prompts.")
        prompt = self.prompts[self.prompt_index]
        self.prompt_index += 1
        return prompt

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        """Append a user-assistant exchange to the history."""
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()


