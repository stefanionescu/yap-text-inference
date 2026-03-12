"""Conversation session dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from .metrics import StartPayloadMode


@dataclass
class ConversationSession:
    """Track state for a multi-turn conversation session."""

    session_id: str
    gender: str
    personality: str
    chat_prompt: str
    sampling: dict[str, float | int] | None = None
    start_payload_mode: StartPayloadMode = "all"


__all__ = ["ConversationSession"]
