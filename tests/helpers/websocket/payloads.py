"""Shared WebSocket message payload builders.

This module provides the canonical `build_start_payload` function used by all
test scripts to construct the start message for WebSocket sessions. Previously
duplicated across 6+ files, this is now the single source of truth.

Payload Types:
    - start: Initial message to begin a conversation turn
    - chat_prompt: Mid-session persona/prompt update
"""

from __future__ import annotations

from typing import Any

from tests.config import DEFAULT_PERSONALITIES
from tests.helpers.metrics import SessionContext


def build_start_payload(
    ctx: SessionContext,
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
    personalities: list[str] | None = None,
) -> dict[str, Any]:
    """Build the start message payload for a conversation turn.
    
    Args:
        ctx: Session context with gender, personality, and chat_prompt.
        user_text: The user's message text.
        history: Conversation history as [{role, content}, ...] (default empty).
        personalities: Optional personality list override (default DEFAULT_PERSONALITIES).
    
    Returns:
        A dict ready to be JSON-serialized and sent over WebSocket.
        
    Raises:
        ValueError: If chat_prompt is empty.
    """
    if not ctx.chat_prompt:
        raise ValueError(
            "chat_prompt is required. "
            "Use select_chat_prompt(gender) to get a valid prompt."
        )
    
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": ctx.session_id,
        "gender": ctx.gender,
        "personality": ctx.personality,
        "personalities": personalities if personalities is not None else DEFAULT_PERSONALITIES,
        "chat_prompt": ctx.chat_prompt,
        "history": history if history is not None else [],
        "user_utterance": user_text,
    }
    if ctx.sampling:
        payload["sampling"] = ctx.sampling
    return payload


def build_chat_prompt_payload(
    ctx: SessionContext,
) -> dict[str, Any]:
    """Build a chat_prompt update payload for mid-session persona changes.
    
    Args:
        ctx: Session context with the new persona settings.
    
    Returns:
        A dict ready to be JSON-serialized and sent over WebSocket.
    """
    return {
        "type": "chat_prompt",
        "session_id": ctx.session_id,
        "gender": ctx.gender,
        "personality": ctx.personality,
        "chat_prompt": ctx.chat_prompt,
    }


__all__ = [
    "build_start_payload",
    "build_chat_prompt_payload",
]

