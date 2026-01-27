"""Session handler orchestration logic.

This module implements the central session management for the inference server.
SessionHandler coordinates per-connection state including lifecycle, configuration,
history, request tracking, and rate limiting.

The global `session_handler` singleton is instantiated in the `instances` module.
For abort functionality, see the `abort` module.
"""

from __future__ import annotations

import copy
import time
import asyncio
from typing import Any

from src.config import (
    CHAT_MODEL,
    TOOL_MODEL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
)

from .history import HistoryController
from .requests import CANCELLED_SENTINEL
from .config import resolve_screen_prefix
from .time import format_session_timestamp
from .requests import has_running_task as _has_running
from .state import SESSION_IDLE_TTL_SECONDS, SessionState
from .config import update_session_config as _update_config
from .requests import is_request_cancelled as _is_cancelled
from .requests import cancel_session_requests as _cancel_requests
from .requests import cleanup_session_requests as _cleanup_requests
from ...tokens.prefix import count_prefix_tokens, strip_screen_prefix, get_effective_user_utt_max_tokens


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

    CANCELLED_SENTINEL = CANCELLED_SENTINEL

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
        new_state.check_screen_prefix_tokens = count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        new_state.screen_checked_prefix_tokens = count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
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
        return _update_config(
            state,
            chat_gender=chat_gender,
            chat_personality=chat_personality,
            chat_prompt=chat_prompt,
            chat_sampling=chat_sampling,
            check_screen_prefix=check_screen_prefix,
            screen_checked_prefix=screen_checked_prefix,
        )

    def get_session_config(self, session_id: str) -> dict[str, Any]:
        """Return a copy of the current session configuration."""
        state = self._get_state(session_id)
        if not state:
            return {}
        state.touch()
        return copy.deepcopy(state.meta)

    def get_check_screen_prefix(self, session_id: str | None) -> str:
        """Resolve the check-screen prefix for the given session."""
        state = self._get_state(session_id) if session_id else None
        return resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)

    def get_screen_checked_prefix(self, session_id: str | None) -> str:
        """Resolve the screen-checked prefix for the given session."""
        state = self._get_state(session_id) if session_id else None
        return resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)


    def clear_session_state(self, session_id: str) -> None:
        """Drop all in-memory data for a session."""
        state = self._sessions.pop(session_id, None)
        if state and state.task and not state.task.done():
            state.task.cancel()

    def get_session_duration(self, session_id: str) -> float:
        """Return the elapsed time since the session was created."""
        state = self._get_state(session_id)
        return max(0.0, time.monotonic() - state.created_at) if state else 0.0

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

    def set_history_messages(self, session_id: str, messages: list[dict]) -> str:
        """Set history from JSON message array [{role, content}, ...].
        
        Parses messages into turns, trims to fit token budget.
        """
        state = self._ensure_state(session_id)
        rendered = self._history.set_messages(state, messages)
        state.touch()
        return rendered

    def get_history_turn_count(self, session_id: str) -> int:
        """Get the number of history turns currently stored for a session."""
        state = self._get_state(session_id)
        return len(state.history_turns) if state else 0

    def append_user_utterance(self, session_id: str, user_utt: str) -> str | None:
        state = self._ensure_state(session_id)
        normalized_user = strip_screen_prefix(
            user_utt or "",
            self.get_check_screen_prefix(session_id),
            self.get_screen_checked_prefix(session_id),
        )
        turn_id = self._history.append_user_turn(state, normalized_user)
        state.touch()
        return turn_id

    def append_history_turn(
        self, session_id: str, user_utt: str, assistant_text: str, *, turn_id: str | None = None
    ) -> str:
        state = self._ensure_state(session_id)
        normalized_user = strip_screen_prefix(
            user_utt or "",
            self.get_check_screen_prefix(session_id),
            self.get_screen_checked_prefix(session_id),
        )
        rendered = self._history.append_turn(state, normalized_user, assistant_text, turn_id=turn_id)
        state.touch()
        return rendered

    # ============================================================================
    # Request/task tracking
    # ============================================================================

    def set_active_request(self, session_id: str, request_id: str) -> None:
        self._ensure_state(session_id).active_request_id = request_id

    def set_tool_request(self, session_id: str, request_id: str) -> None:
        self._ensure_state(session_id).tool_request_id = request_id

    def get_tool_request_id(self, session_id: str) -> str:
        state = self._get_state(session_id)
        return state.tool_request_id or "" if state else ""

    def clear_tool_request_id(self, session_id: str) -> None:
        state = self._get_state(session_id)
        if state:
            state.tool_request_id = None

    def is_request_cancelled(self, session_id: str, request_id: str) -> bool:
        return _is_cancelled(self._get_state(session_id), request_id)

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
        return _has_running(self._get_state(session_id))

    def cancel_session_requests(self, session_id: str) -> None:
        state = self._get_state(session_id)
        if state:
            _cancel_requests(state)

    def cleanup_session_requests(self, session_id: str) -> dict[str, str]:
        return _cleanup_requests(self._get_state(session_id))

    # ============================================================================
    # Token budget helpers
    # ============================================================================

    def get_effective_user_utt_max_tokens(self, session_id: str | None, *, for_followup: bool = False) -> int:
        """Get the effective max tokens for user utterance after accounting for prefix."""
        state = self._get_state(session_id) if session_id else None
        return get_effective_user_utt_max_tokens(state, for_followup=for_followup)

    # ============================================================================
    # Internal helpers
    # ============================================================================

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


__all__ = ["SessionHandler"]
