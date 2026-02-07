"""Conversation session dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ConversationSession:
    """Track state for a multi-turn conversation session."""

    session_id: str
    gender: str
    personality: str
    chat_prompt: str
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant exchange to the conversation history."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


__all__ = ["ConversationSession"]
