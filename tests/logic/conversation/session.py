"""Conversation session state management.

This module provides the ConversationSession dataclass that tracks session
state (ID, gender, personality, history) and builds the start payload for
each exchange. It maintains conversation history across multiple turns.
"""

from __future__ import annotations

from typing import Any
from dataclasses import field, dataclass

from tests.helpers.metrics import SessionContext
from tests.helpers.websocket import build_start_payload as build_ws_start_payload


@dataclass
class ConversationSession:
    """Track state for a multi-turn conversation session.
    
    Note: chat_prompt is required - the server requires a system prompt
    when DEPLOY_CHAT is enabled.
    """

    session_id: str
    gender: str
    personality: str
    chat_prompt: str  # Required - use select_chat_prompt(gender) to get one
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant exchange to the conversation history."""
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


def build_start_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    """Build the start message payload for a conversation turn.
    
    Raises:
        ValueError: If chat_prompt is empty.
    """
    ctx = SessionContext(
        session_id=session.session_id,
        gender=session.gender,
        personality=session.personality,
        chat_prompt=session.chat_prompt,
        sampling=session.sampling,
    )
    return build_ws_start_payload(ctx, user_text, history=session.history)


__all__ = ["ConversationSession", "build_start_payload"]
