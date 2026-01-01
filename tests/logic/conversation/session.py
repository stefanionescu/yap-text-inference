"""Conversation session state management.

This module provides the ConversationSession dataclass that tracks session
state (ID, gender, personality, history) and builds the start payload for
each exchange. It maintains conversation history across multiple turns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from tests.config import DEFAULT_PERSONALITIES


@dataclass
class ConversationSession:
    """Track state for a multi-turn conversation session."""

    session_id: str
    gender: str
    personality: str
    chat_prompt: str | None
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant exchange to the conversation history."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


def build_start_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    """Build the start message payload for a conversation turn."""
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session.session_id,
        "gender": session.gender,
        "personality": session.personality,
        "personalities": DEFAULT_PERSONALITIES,
        "history": session.history,
        "user_utterance": user_text,
    }
    if session.chat_prompt is not None:
        payload["chat_prompt"] = session.chat_prompt
    if session.sampling:
        payload["sampling"] = session.sampling
    return payload


__all__ = ["ConversationSession", "build_start_payload"]
