"""Session-scoped dataclasses and shared state helpers.

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

Configuration:
    SESSION_IDLE_TTL_SECONDS: How long idle sessions are kept in memory.
        Defaults to 1800 seconds (30 minutes).
        Set via environment variable.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any

from ..rate_limit import SlidingWindowRateLimiter

# Sessions are evicted after this many seconds of inactivity
SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "1800"))


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
        session_id: Unique identifier for this session (typically WebSocket ID).
        meta: Session metadata dict (timestamps, model info, persona config).
        history_turns: Ordered list of conversation turns.
        task: Currently running asyncio.Task for this session (for cancellation).
        active_request_id: ID of the current chat/generation request.
        tool_request_id: ID of the current tool/classifier request.
        created_at: Monotonic timestamp when session was created.
        last_access: Monotonic timestamp of last activity (for TTL eviction).
        chat_prompt_last_update_at: When the chat prompt was last updated.
        chat_prompt_rate_limiter: Rate limiter for persona updates.
        personalities: Mapping of personality names to synonyms (for matching).
        used_control_messages: Set of control messages already shown (for variety).
        check_screen_prefix_tokens: Cached token count for screenshot prefix.
        screen_checked_prefix_tokens: Cached token count for followup prefix.
    """

    session_id: str
    meta: dict[str, Any]
    history_turns: list[HistoryTurn] = field(default_factory=list)
    task: asyncio.Task | None = None  # For cancellation
    active_request_id: str | None = None  # Chat request tracking
    tool_request_id: str | None = None  # Tool request tracking
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)
    chat_prompt_last_update_at: float = 0.0
    chat_prompt_rate_limiter: SlidingWindowRateLimiter | None = None
    # Personality mapping: {personality_name: [synonym1, synonym2, ...]}
    # Set on connection via start message
    personalities: dict[str, list[str]] | None = None
    # Track used control messages to ensure variety (reset when all used)
    used_control_messages: set[str] = field(default_factory=set)
    # Cached token counts for screen prefixes (computed once when prefixes are set)
    check_screen_prefix_tokens: int = 0
    screen_checked_prefix_tokens: int = 0

    def touch(self) -> None:
        """Mark the session as active.
        
        Updates last_access timestamp to prevent idle eviction.
        """

        self.last_access = time.monotonic()


