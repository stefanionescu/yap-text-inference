"""Conversation session state management.

This module provides the ConversationSession dataclass that tracks session
state (ID, gender, personality, history) and builds the bootstrap payload for
the first exchange. It maintains conversation history across multiple turns.
"""

from __future__ import annotations

from typing import Any
from tests.state import SessionContext, ConversationSession
from tests.support.helpers.websocket import (
    build_start_payload as build_ws_start_payload,
    build_message_payload as build_ws_message_payload,
)


def build_start_payload(session: ConversationSession) -> dict[str, Any]:
    """Build the bootstrap-only start payload for a conversation turn."""
    ctx = SessionContext(
        session_id=session.session_id,
        gender=session.gender,
        personality=session.personality,
        chat_prompt=session.chat_prompt,
        sampling=session.sampling,
        start_payload_mode=session.start_payload_mode,
    )
    return build_ws_start_payload(ctx)


def build_message_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    """Build the message payload for subsequent conversation turns."""
    return build_ws_message_payload(
        user_text,
        sampling=session.sampling,
    )


__all__ = ["build_message_payload", "build_start_payload"]
