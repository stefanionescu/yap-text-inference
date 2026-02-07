"""Shared WebSocket message payload builders.

This module provides the canonical `build_start_payload` function used by all
test scripts to construct the start message for WebSocket sessions.

Payload Type:
    - start: Initial message to begin a conversation turn
"""

from __future__ import annotations

import uuid
from typing import Any

from tests.state import SessionContext


def build_envelope(
    msg_type: str,
    session_id: str,
    request_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Build a standard envelope for websocket messages."""
    return {
        "type": msg_type,
        "session_id": session_id,
        "request_id": request_id,
        "payload": payload,
    }


def build_cancel_payload(session_id: str, request_id: str) -> dict[str, Any]:
    """Build a cancel message for the given request."""
    return build_envelope("cancel", session_id, request_id, {"reason": "client_request"})


def build_end_payload(session_id: str, request_id: str | None = None) -> dict[str, Any]:
    """Build an end message for the given session."""
    rid = request_id or f"end-{uuid.uuid4()}"
    return build_envelope("end", session_id, rid, {})


def build_start_payload(
    ctx: SessionContext,
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
    request_id: str | None = None,
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
        raise ValueError(
            "chat_prompt is required. "
            "Use select_chat_prompt(gender) to get a valid prompt."
        )
    
    inner_payload: dict[str, Any] = {
        "gender": ctx.gender,
        "personality": ctx.personality,
        "chat_prompt": ctx.chat_prompt,
        "history": history if history is not None else [],
        "user_utterance": user_text,
    }
    if ctx.sampling:
        inner_payload["sampling"] = ctx.sampling
    rid = request_id or f"req-{uuid.uuid4()}"
    return build_envelope("start", ctx.session_id, rid, inner_payload)


__all__ = [
    "build_cancel_payload",
    "build_end_payload",
    "build_envelope",
    "build_start_payload",
]
