"""Shared WebSocket message payload builders.

This module provides canonical payload builders for WebSocket test messages.
All messages use the flat format (no envelope wrapper).
"""

from __future__ import annotations

from typing import Any
from tests.support.state.metrics import SessionContext


def build_cancel_payload() -> dict[str, Any]:
    """Build a cancel message."""
    return {"type": "cancel"}


def build_end_payload() -> dict[str, Any]:
    """Build an end message."""
    return {"type": "end"}


def build_message_payload(
    user_text: str,
    *,
    sampling: dict[str, float | int] | None = None,
) -> dict[str, Any]:
    """Build a message payload for subsequent conversation turns.

    Args:
        user_text: The user's message text.
        sampling: Optional sampling parameter overrides.

    Returns:
        A dict ready to be JSON-serialized and sent over WebSocket.
    """
    msg: dict[str, Any] = {"type": "message", "user_utterance": user_text}
    if sampling:
        msg["sampling"] = sampling
    return msg


def build_start_payload(
    ctx: SessionContext,
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the start message payload for a conversation turn.

    Args:
        ctx: Session context with gender, personality, and chat_prompt.
        user_text: The user's message text.
        history: Conversation history as [{role, content}, ...] (default empty).

    Returns:
        A dict ready to be JSON-serialized and sent over WebSocket.

    Raises:
        ValueError: If chat_prompt is empty.
    """
    if not ctx.chat_prompt:
        raise ValueError("chat_prompt is required. Use select_chat_prompt(gender) to get a valid prompt.")

    msg: dict[str, Any] = {
        "type": "start",
        "gender": ctx.gender,
        "personality": ctx.personality,
        "chat_prompt": ctx.chat_prompt,
        "history": history if history is not None else [],
        "user_utterance": user_text,
    }
    if ctx.sampling:
        msg["sampling"] = ctx.sampling
    return msg


__all__ = [
    "build_cancel_payload",
    "build_end_payload",
    "build_message_payload",
    "build_start_payload",
]
