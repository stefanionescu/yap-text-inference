"""Session handler orchestration logic.

This module implements the central session management for the inference server.
SessionHandler is responsible for:

1. Session Lifecycle:
   - Creating new sessions with default metadata
   - Tracking session activity (last access time)
   - Evicting idle sessions based on TTL

2. Configuration Management:
   - Storing and updating persona (gender, personality, chat_prompt)
   - Managing sampling parameters per session
   - Handling custom screen prefixes

3. History Management:
   - Delegating to HistoryController for conversation history
   - Normalizing user utterances (stripping prefixes)
   - Providing separate history views for chat vs tool models

4. Request Tracking:
   - Tracking active chat and tool request IDs
   - Detecting cancelled requests
   - Managing asyncio.Task references for cleanup

5. Rate Limiting:
   - Per-session rate limiters for chat prompt updates
   - Tracking last update timestamps

The global `session_handler` instance is used throughout the application.
The `abort_session_requests` helper provides clean shutdown of active work.
"""

from __future__ import annotations

import asyncio
import copy
import time
from typing import Any

from src.config import (
    CHAT_MODEL,
    TOOL_MODEL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
    USER_UTT_MAX_TOKENS,
)
from src.tokens import count_tokens_chat
from ..rate_limit import RateLimitError, SlidingWindowRateLimiter
from .time import format_session_timestamp

from .history import HistoryController
from .state import SessionState, SESSION_IDLE_TTL_SECONDS


class SessionHandler:
    """Handles session metadata, request tracking, and lifecycle.
    
    This is the central coordinator for per-connection session state.
    It maintains an in-memory dictionary of SessionState objects keyed
    by session_id (typically a WebSocket connection identifier).
    
    Thread Safety:
        All operations are designed for single-threaded async code.
        The handler is not thread-safe for concurrent access.
    
    Attributes:
        CANCELLED_SENTINEL: Special value indicating a cancelled session.
    """

    CANCELLED_SENTINEL = "__CANCELLED__"

    def __init__(self, idle_ttl_seconds: int = SESSION_IDLE_TTL_SECONDS):
        """Initialize the session handler.
        
        Args:
            idle_ttl_seconds: Time in seconds before idle sessions are evicted.
                Defaults to SESSION_IDLE_TTL_SECONDS from environment.
        """
        self._sessions: dict[str, SessionState] = {}  # session_id -> state
        self._idle_ttl_seconds = idle_ttl_seconds
        self._history = HistoryController()  # Shared history helper

    def _get_state(self, session_id: str) -> SessionState | None:
        """Get session state if it exists (without touching)."""
        return self._sessions.get(session_id)

    def _ensure_state(self, session_id: str) -> SessionState:
        """Get or create session state, marking it as accessed."""
        state = self._sessions.get(session_id)
        if state is None:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        else:
            state.touch()
        return state

    # ============================================================================
    # Session metadata / lifecycle
    # ============================================================================
    def initialize_session(self, session_id: str) -> dict[str, Any]:
        """Ensure a session state exists and return its metadata."""

        self._evict_idle_sessions()
        state = self._sessions.get(session_id)
        if state:
            state.touch()
            return state.meta

        timestamp = format_session_timestamp()
        meta = {
            "now_iso": timestamp.iso,
            "now_str": timestamp.display,
            "now_classification": timestamp.classification,
            "now_tz": timestamp.tz,
            "chat_gender": None,
            "chat_personality": None,
            "chat_prompt": None,
            "chat_sampling": None,
            "chat_model": CHAT_MODEL if DEPLOY_CHAT else None,
            "tool_model": TOOL_MODEL if DEPLOY_TOOL else None,
            "check_screen_prefix": None,
            "screen_checked_prefix": None,
        }
        new_state = SessionState(session_id=session_id, meta=meta)
        # Cache default prefix token counts
        new_state.check_screen_prefix_tokens = self._count_prefix_tokens(
            DEFAULT_CHECK_SCREEN_PREFIX
        )
        new_state.screen_checked_prefix_tokens = self._count_prefix_tokens(
            DEFAULT_SCREEN_CHECKED_PREFIX
        )
        self._sessions[session_id] = new_state
        new_state.touch()
        return meta

    def update_session_config(
        self,
        session_id: str,
        chat_gender: str | None = None,
        chat_personality: str | None = None,
        chat_prompt: str | None = None,
        chat_sampling: dict[str, Any] | None = None,
        check_screen_prefix: str | None = None,
        screen_checked_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Update mutable persona configuration for a session."""

        state = self._ensure_state(session_id)
        meta = state.meta

        changed: dict[str, Any] = {}
        if chat_gender is not None:
            meta["chat_gender"] = chat_gender
            changed["chat_gender"] = chat_gender

        if chat_personality is not None:
            cpers = chat_personality or None
            if isinstance(cpers, str):
                cpers = cpers.lower()
            meta["chat_personality"] = cpers
            changed["chat_personality"] = cpers

        if chat_prompt is not None:
            cp = chat_prompt or None
            meta["chat_prompt"] = cp
            changed["chat_prompt"] = bool(cp)

        if chat_sampling is not None:
            sampling = chat_sampling or None
            if isinstance(sampling, dict):
                sampling_copy = sampling.copy()
            else:
                sampling_copy = None
            meta["chat_sampling"] = sampling_copy
            changed["chat_sampling"] = (
                sampling_copy.copy() if isinstance(sampling_copy, dict) else None
            )

        if check_screen_prefix is not None:
            normalized = (check_screen_prefix or "").strip() or None
            meta["check_screen_prefix"] = normalized
            changed["check_screen_prefix"] = normalized
            # Recompute token count: use custom prefix or fall back to default
            effective_prefix = normalized or DEFAULT_CHECK_SCREEN_PREFIX
            state.check_screen_prefix_tokens = self._count_prefix_tokens(effective_prefix)

        if screen_checked_prefix is not None:
            normalized_checked = (screen_checked_prefix or "").strip() or None
            meta["screen_checked_prefix"] = normalized_checked
            changed["screen_checked_prefix"] = normalized_checked
            # Recompute token count: use custom prefix or fall back to default
            effective_prefix = normalized_checked or DEFAULT_SCREEN_CHECKED_PREFIX
            state.screen_checked_prefix_tokens = self._count_prefix_tokens(effective_prefix)

        return changed

    def get_chat_prompt_last_update_at(self, session_id: str) -> float:
        state = self._ensure_state(session_id)
        return float(state.chat_prompt_last_update_at or 0.0)

    def set_chat_prompt_last_update_at(self, session_id: str, timestamp: float) -> None:
        state = self._ensure_state(session_id)
        state.chat_prompt_last_update_at = timestamp

    def consume_chat_prompt_update(
        self,
        session_id: str,
        *,
        limit: int,
        window_seconds: float,
    ) -> float:
        """Record a chat prompt update attempt if within the rolling window limit.

        Returns:
            float: 0 if allowed, otherwise the number of seconds until the next slot frees.
        """

        state = self._ensure_state(session_id)
        limiter = state.chat_prompt_rate_limiter
        if (
            limiter is None
            or limiter.limit != limit
            or limiter.window_seconds != window_seconds
        ):
            limiter = SlidingWindowRateLimiter(limit=limit, window_seconds=window_seconds)
            state.chat_prompt_rate_limiter = limiter

        try:
            limiter.consume()
        except RateLimitError as err:
            return err.retry_in

        state.chat_prompt_last_update_at = time.monotonic()
        return 0.0

    def get_session_config(self, session_id: str) -> dict[str, Any]:
        """Return a copy of the current session configuration."""

        state = self._get_state(session_id)
        if not state:
            return {}
        state.touch()
        return copy.deepcopy(state.meta)

    def get_check_screen_prefix(self, session_id: str | None) -> str:
        """Resolve the check-screen prefix for the given session."""
        resolved_default = (DEFAULT_CHECK_SCREEN_PREFIX or "").strip()
        if not session_id:
            return resolved_default
        state = self._get_state(session_id)
        if not state:
            return resolved_default
        prefix = (state.meta.get("check_screen_prefix") or "").strip()
        return prefix or resolved_default

    def get_screen_checked_prefix(self, session_id: str | None) -> str:
        """Resolve the screen-checked prefix for the given session."""
        resolved_default = (DEFAULT_SCREEN_CHECKED_PREFIX or "").strip()
        if not session_id:
            return resolved_default
        state = self._get_state(session_id)
        if not state:
            return resolved_default
        prefix = (state.meta.get("screen_checked_prefix") or "").strip()
        return prefix or resolved_default

    def set_personalities(
        self, session_id: str, personalities: dict[str, list[str]] | None
    ) -> None:
        """Store the personalities configuration for a session."""
        state = self._ensure_state(session_id)
        state.personalities = personalities

    def get_personalities(self, session_id: str) -> dict[str, list[str]] | None:
        """Get the personalities configuration for a session."""
        state = self._get_state(session_id)
        if not state:
            return None
        return state.personalities

    def pick_control_message(self, session_id: str) -> str:
        """Pick a random control message for this session.
        
        Messages are cycled to ensure variety - once all messages
        have been used in a session, the pool resets.
        """
        from src.execution.tool.messages import pick_control_message
        
        state = self._ensure_state(session_id)
        return pick_control_message(state)

    def clear_session_state(self, session_id: str) -> None:
        """Drop all in-memory data for a session."""

        state = self._sessions.pop(session_id, None)
        if state and state.task and not state.task.done():
            state.task.cancel()

    def get_session_duration(self, session_id: str) -> float:
        """Return the elapsed time since the session was created."""

        state = self._get_state(session_id)
        if not state:
            return 0.0
        return max(0.0, time.monotonic() - state.created_at)

    # ============================================================================
    # History helpers
    # ============================================================================
    def get_history_text(self, session_id: str) -> str:
        state = self._get_state(session_id)
        if not state:
            return ""
        state.touch()
        return self._history.get_text(state)
    
    def get_user_texts(self, session_id: str) -> list[str]:
        """Get raw user texts (untrimmed)."""
        state = self._get_state(session_id)
        if not state:
            return []
        state.touch()
        return self._history.get_user_texts(state)

    def get_tool_history_text(self, session_id: str) -> str:
        """Get trimmed history tailored for the classifier/tool model."""
        state = self._get_state(session_id)
        if not state:
            return ""
        state.touch()
        return self._history.get_tool_history_text(state)

    def set_history_text(self, session_id: str, history_text: str) -> str:
        state = self._ensure_state(session_id)
        rendered = self._history.set_text(state, history_text)
        state.touch()
        return rendered

    def append_user_utterance(self, session_id: str, user_utt: str) -> str | None:
        state = self._ensure_state(session_id)
        normalized_user = self._strip_check_screen_prefix(session_id, user_utt or "")
        turn_id = self._history.append_user_turn(state, normalized_user)
        state.touch()
        return turn_id

    def append_history_turn(
        self,
        session_id: str,
        user_utt: str,
        assistant_text: str,
        *,
        turn_id: str | None = None,
    ) -> str:
        state = self._ensure_state(session_id)
        normalized_user = self._strip_check_screen_prefix(session_id, user_utt or "")
        rendered = self._history.append_turn(
            state,
            normalized_user,
            assistant_text,
            turn_id=turn_id,
        )
        state.touch()
        return rendered

    # ============================================================================
    # Request/task tracking
    # ============================================================================
    def set_active_request(self, session_id: str, request_id: str) -> None:
        state = self._ensure_state(session_id)
        state.active_request_id = request_id

    def set_tool_request(self, session_id: str, request_id: str) -> None:
        state = self._ensure_state(session_id)
        state.tool_request_id = request_id

    def get_tool_request_id(self, session_id: str) -> str:
        state = self._get_state(session_id)
        return state.tool_request_id or "" if state else ""

    def clear_tool_request_id(self, session_id: str) -> None:
        state = self._get_state(session_id)
        if state:
            state.tool_request_id = None

    def is_request_cancelled(self, session_id: str, request_id: str) -> bool:
        state = self._get_state(session_id)
        if not state:
            return True
        active = state.active_request_id
        if active == self.CANCELLED_SENTINEL:
            return True
        if not active:
            return False
        return active != request_id

    def track_task(self, session_id: str, task: asyncio.Task) -> None:
        state = self._ensure_state(session_id)
        state.task = task

        def _clear_task(completed: asyncio.Task) -> None:
            current = self._get_state(session_id)
            if current and current.task is completed:
                current.task = None
                current.touch()

        task.add_done_callback(_clear_task)

    def has_running_task(self, session_id: str) -> bool:
        state = self._get_state(session_id)
        return bool(state and state.task and not state.task.done())

    def cancel_session_requests(self, session_id: str) -> None:
        state = self._get_state(session_id)
        if not state:
            return
        state.active_request_id = self.CANCELLED_SENTINEL
        if state.task and not state.task.done():
            state.task.cancel()

    def cleanup_session_requests(self, session_id: str) -> dict[str, str]:
        state = self._get_state(session_id)
        if not state:
            return {"active": "", "tool": ""}
        active_req = (
            state.active_request_id
            if state.active_request_id not in (None, self.CANCELLED_SENTINEL)
            else ""
        )
        tool_req = state.tool_request_id or ""
        state.active_request_id = None
        state.tool_request_id = None
        return {"active": active_req, "tool": tool_req}

    # ============================================================================
    # Token budget helpers
    # ============================================================================
    def _count_prefix_tokens(self, prefix: str | None) -> int:
        """Count tokens for a prefix string (including trailing space)."""
        if not prefix:
            return 0
        # Include the space that will be added when prefixing
        return count_tokens_chat(f"{prefix.strip()} ")

    def get_effective_user_utt_max_tokens(
        self,
        session_id: str | None,
        *,
        for_followup: bool = False,
    ) -> int:
        """Get the effective max tokens for user utterance after accounting for prefix.

        Args:
            session_id: The session ID to look up prefix token counts.
            for_followup: If True, account for screen_checked_prefix (followup messages).
                          If False, account for check_screen_prefix (start messages
                          that may trigger screenshot).

        Returns:
            The adjusted max token count for the user message content.
        """
        if not session_id:
            # No session: use defaults
            if for_followup:
                prefix_tokens = self._count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
            else:
                prefix_tokens = self._count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
            return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

        state = self._get_state(session_id)
        if not state:
            # Session not found: use defaults
            if for_followup:
                prefix_tokens = self._count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
            else:
                prefix_tokens = self._count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
            return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

        if for_followup:
            prefix_tokens = state.screen_checked_prefix_tokens
        else:
            prefix_tokens = state.check_screen_prefix_tokens

        return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

    # ============================================================================
    # Internal helpers
    # ============================================================================
    def _strip_check_screen_prefix(self, session_id: str, text: str) -> str:
        """Remove any session-specific screen prefixes from stored history."""

        if not text:
            return ""

        def _strip_prefix(candidate: str | None, value: str) -> tuple[bool, str]:
            if not candidate:
                return False, value
            prefix_text = candidate.strip()
            if not prefix_text:
                return False, value
            prefix_len = len(candidate)
            if value.startswith(candidate):
                return True, value[prefix_len:].lstrip()
            lower_candidate = candidate.lower()
            if value.lower().startswith(lower_candidate):
                return True, value[prefix_len:].lstrip()
            return False, value

        prefixes: list[str] = []
        for candidate in (
            self.get_check_screen_prefix(session_id),
            self.get_screen_checked_prefix(session_id),
        ):
            if candidate and candidate not in prefixes:
                prefixes.append(candidate)

        for prefix in prefixes:
            removed, updated = _strip_prefix(prefix, text)
            if removed:
                return updated

        return text

    def _evict_idle_sessions(self) -> None:
        if self._idle_ttl_seconds <= 0:
            return
        cutoff = time.monotonic() - self._idle_ttl_seconds
        expired = [
            session_id
            for session_id, state in self._sessions.items()
            if state.last_access < cutoff and (not state.task or state.task.done())
        ]
        for session_id in expired:
            self.clear_session_state(session_id)


session_handler = SessionHandler()


async def abort_session_requests(
    session_id: str | None,
    *,
    clear_state: bool = False,
) -> dict[str, str]:
    """Cancel tracked session requests and best-effort abort engine work."""

    if not session_id:
        return {"active": "", "tool": ""}

    session_handler.cancel_session_requests(session_id)
    req_info = session_handler.cleanup_session_requests(session_id)

    if DEPLOY_CHAT and req_info.get("active"):
        try:
            from src.engines import get_engine  # local import to avoid cycles

            await (await get_engine()).abort(req_info["active"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if clear_state:
        session_handler.clear_session_state(session_id)

    return req_info
