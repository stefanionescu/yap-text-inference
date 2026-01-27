"""Session-scoped dataclasses for per-connection state.

This module defines the core data structures for session state:

HistoryTurn:
    Represents a single exchange in the conversation. Each turn has:
    - turn_id: UUID for tracking (used for streaming updates)
    - user: The user's message
    - assistant: The assistant's response (may be empty during streaming)

SessionState:
    Container for all per-session mutable data including:
    - Metadata (timestamps, model info, persona config)
    - Conversation history
    - Request tracking (active request IDs, asyncio.Task)
    - Rate limiting state
    - Token budget caches
"""

from __future__ import annotations

import time
import asyncio
from typing import Any
from dataclasses import field, dataclass


@dataclass
class HistoryTurn:
    """One user/assistant exchange in the running conversation.
    
    During streaming generation, assistant may be empty until
    the response is complete.
    
    Attributes:
        turn_id: Unique identifier for this turn (UUID hex string).
        user: The user's message for this turn.
        assistant: The assistant's response (empty during streaming).
    """

    turn_id: str
    user: str
    assistant: str


@dataclass
class SessionState:
    """Container for all mutable session-scoped data.

    This dataclass holds everything needed to manage a single user session,
    from conversation history to request tracking to rate limiting.

    Attributes:
        session_id: Unique identifier for this session. Typically the WebSocket
            connection ID, used for logging and session lookup.
        meta: Extensible metadata dictionary containing session configuration.
            Common keys include 'model', 'persona', 'temperature', and timestamps.
        history_turns: Chronologically ordered list of conversation exchanges.
            Each turn pairs a user message with the assistant's response.
        task: Reference to the currently running asyncio.Task for this session.
            Used to cancel in-flight generation when a new request arrives or
            the connection closes. None when no generation is active.
        active_request_id: Tracks the current chat/generation request. Used to
            detect stale streaming responses when a newer request supersedes
            an older one. None when idle.
        tool_request_id: Tracks the current tool/classifier request separately
            from chat requests. Allows concurrent tool classification while
            chat generation is in progress. None when no tool request is active.
        created_at: Monotonic timestamp (from time.monotonic) when the session
            was first created. Used for session age metrics and debugging.
        last_access: Monotonic timestamp of the most recent activity on this
            session. Updated via touch() on each request. Used by the session
            manager to evict idle sessions after TTL expiry.
        check_screen_prefix_tokens: Cached token count for the "check_screen"
            system prefix. Computed once when the prefix is set to avoid
            repeated tokenization during context budget calculations.
        screen_checked_prefix_tokens: Cached token count for the "screen_checked"
            followup prefix. Computed once when set, similar to check_screen.
    """

    session_id: str
    meta: dict[str, Any]
    history_turns: list[HistoryTurn] = field(default_factory=list)
    task: asyncio.Task | None = None
    active_request_id: str | None = None
    tool_request_id: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)
    check_screen_prefix_tokens: int = 0
    screen_checked_prefix_tokens: int = 0

    def touch(self) -> None:
        """Mark the session as active.
        
        Updates last_access timestamp to prevent idle eviction.
        """
        self.last_access = time.monotonic()


__all__ = ["HistoryTurn", "SessionState"]

