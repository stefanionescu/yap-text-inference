"""Conversation session state management.

This module provides the ConversationSession dataclass that tracks session
state (ID, gender, personality, history) and builds the start payload for
each exchange. It maintains conversation history across multiple turns.
"""

from __future__ import annotations

from typing import Any
from tests.state import SessionContext, ConversationSession
from tests.helpers.websocket import (
    build_start_payload as build_ws_start_payload,
    build_message_payload as build_ws_message_payload,
)


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
    return build_ws_start_payload(ctx, user_text)


def build_message_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    """Build the message payload for subsequent conversation turns."""
    return build_ws_message_payload(
        session.session_id,
        user_text,
        sampling=session.sampling,
    )


__all__ = ["build_message_payload", "build_start_payload"]
