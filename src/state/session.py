"""Session-scoped dataclasses for per-connection state."""

from __future__ import annotations

import time
import uuid
import asyncio
from typing import Any, Literal
from dataclasses import field, dataclass


@dataclass
class ChatMessage:
    """One stored chat-history message."""

    role: Literal["user", "assistant"]
    content: str


@dataclass
class HistoryTurn:
    """One stored tool-history entry."""

    turn_id: str
    user: str
    assistant: str


@dataclass
class SessionState:
    """Container for all mutable session-scoped data.

    This dataclass holds everything needed to manage a single user session,
    from conversation history to request tracking to rate limiting.
    Created per-connection; the connection IS the session identity.

    Attributes:
        meta: Extensible metadata dictionary containing session configuration.
        session_id: Stable server-generated ID for this websocket session.
        chat_history_messages: Chat history store, active only when chat
            deployment is enabled.
        tool_history_turns: Tool history store (user-only turns), active only
            when tool deployment is enabled.
        active_request_task: Reference to the currently running asyncio.Task
            for this session.
        active_request_id: Tracks the current chat/generation request. Used
            to detect stale streaming responses when a newer request supersedes
            an older one. None when idle.
        lifecycle_state: Request lifecycle state for transition safety:
            'idle' | 'running' | 'cancelling' | 'closed'.
        cancel_requested: Cooperative cancellation flag for in-flight streams.
        request_lock: Lock guarding lifecycle/request mutation transitions.
        created_at: Monotonic timestamp when the session was first created.
        check_screen_prefix_tokens: Cached token count for the "check_screen" prefix.
        screen_checked_prefix_tokens: Cached token count for the "screen_checked" prefix.
        screen_followup_pending: Whether the next client message should be
            prefixed with screen_checked_prefix for chat generation.
    """

    meta: dict[str, Any]
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    chat_history_messages: list[ChatMessage] | None = None
    tool_history_turns: list[HistoryTurn] | None = None
    active_request_task: asyncio.Task | None = None
    active_request_id: str | None = None
    lifecycle_state: Literal["idle", "running", "cancelling", "closed"] = "idle"
    cancel_requested: bool = False
    request_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    created_at: float = field(default_factory=time.monotonic)
    check_screen_prefix_tokens: int = 0
    screen_checked_prefix_tokens: int = 0
    screen_followup_pending: bool = False


__all__ = ["ChatMessage", "HistoryTurn", "SessionState"]
