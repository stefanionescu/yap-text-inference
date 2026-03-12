"""Shared WebSocket message payload builders.

This module provides canonical payload builders for WebSocket test messages.
All messages use the flat format (no envelope wrapper).
"""

from __future__ import annotations

from typing import Any
from src.config.websocket import WS_PROTOCOL_VERSION
from tests.state.metrics import SessionContext, StartPayloadMode


def build_cancel_payload() -> dict[str, Any]:
    """Build a cancel message."""
    return {"type": "cancel", "v": WS_PROTOCOL_VERSION}


def build_end_payload() -> dict[str, Any]:
    """Build an end message."""
    return {"type": "end", "v": WS_PROTOCOL_VERSION}


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
    msg: dict[str, Any] = {"type": "message", "v": WS_PROTOCOL_VERSION, "user_utterance": user_text}
    if sampling:
        msg["sampling"] = sampling
    return msg


def resolve_start_payload_mode(
    *,
    deploy_mode: str | None = None,
    deploy_chat: bool | None = None,
    deploy_tool: bool | None = None,
    default: StartPayloadMode = "all",
) -> StartPayloadMode:
    """Resolve the preferred start payload mode from deploy settings."""
    normalized_mode = (deploy_mode or "").strip().lower()
    explicit_mode_map: dict[str, StartPayloadMode] = {
        "both": "all",
        "chat": "chat-only",
        "tool": "tool-only",
    }
    explicit_mode = explicit_mode_map.get(normalized_mode)
    if explicit_mode is not None:
        return explicit_mode
    if deploy_chat and deploy_tool:
        return "all"
    if deploy_chat:
        return "chat-only"
    if deploy_tool:
        return "tool-only"
    return default


def includes_chat_start_fields(mode: StartPayloadMode) -> bool:
    """Return whether a start payload mode should include chat-only fields."""
    return mode != "tool-only"


def build_start_payload(
    ctx: SessionContext,
    user_text: str,
    *,
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Build the start message payload for a conversation turn.

    Args:
        ctx: Session context with optional chat-only start fields.
        user_text: The user's message text.
        history: Conversation history as [{role, content}, ...] (default empty).

    Returns:
        A dict ready to be JSON-serialized and sent over WebSocket.
    """
    msg: dict[str, Any] = {
        "type": "start",
        "v": WS_PROTOCOL_VERSION,
        "history": history if history is not None else [],
        "user_utterance": user_text,
    }
    if includes_chat_start_fields(ctx.start_payload_mode):
        if ctx.gender is not None:
            msg["gender"] = ctx.gender
        if ctx.personality is not None:
            msg["personality"] = ctx.personality
        if ctx.chat_prompt is not None:
            msg["chat_prompt"] = ctx.chat_prompt
        if ctx.sampling is not None:
            msg["sampling"] = ctx.sampling
    return msg


__all__ = [
    "build_cancel_payload",
    "build_end_payload",
    "build_message_payload",
    "build_start_payload",
    "includes_chat_start_fields",
    "resolve_start_payload_mode",
]
