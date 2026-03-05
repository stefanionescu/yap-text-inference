"""Session handler orchestration logic."""

from __future__ import annotations

import copy
import time
import asyncio
import contextlib
from typing import TYPE_CHECKING, Any
from .history import HistoryController
from .time import format_session_timestamp
from src.state.session import HistoryTurn, SessionState
from .config import resolve_screen_prefix, update_session_config as _update_config
from ...tokens.prefix import count_prefix_tokens, strip_screen_prefix, get_effective_user_utt_max_tokens
from src.config import (
    CHAT_MODEL,
    TOOL_MODEL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
)
from .requests import (
    CANCELLED_SENTINEL,
    has_running_task as _has_running,
    is_request_cancelled as _is_cancelled,
    cancel_session_requests as _cancel_requests,
    cleanup_session_requests as _cleanup_requests,
)

if TYPE_CHECKING:
    from src.engines.base import BaseEngine


class SessionHandler:
    """Stateless helper for session metadata, request tracking, and lifecycle.

    Methods operate on a SessionState passed by the caller (per-connection).
    No internal session dict or eviction logic — the connection IS the session.
    """

    CANCELLED_SENTINEL = CANCELLED_SENTINEL

    def __init__(
        self,
        *,
        chat_engine: BaseEngine | None = None,
    ):
        self._chat_engine = chat_engine
        self._history = HistoryController()

    # ============================================================================
    # Session metadata / lifecycle
    # ============================================================================

    def initialize_session(self, state: SessionState) -> dict[str, Any]:
        """Populate a fresh session state with default metadata."""
        timestamp = format_session_timestamp()
        meta = state.meta
        meta.update(
            {
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
        )
        # Cache default prefix token counts
        state.check_screen_prefix_tokens = count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        state.screen_checked_prefix_tokens = count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
        return meta

    def update_session_config(
        self,
        state: SessionState,
        chat_gender: str | None = None,
        chat_personality: str | None = None,
        chat_prompt: str | None = None,
        chat_sampling: dict[str, Any] | None = None,
        check_screen_prefix: str | None = None,
        screen_checked_prefix: str | None = None,
    ) -> dict[str, Any]:
        """Update mutable persona configuration for a session."""
        return _update_config(
            state,
            chat_gender=chat_gender,
            chat_personality=chat_personality,
            chat_prompt=chat_prompt,
            chat_sampling=chat_sampling,
            check_screen_prefix=check_screen_prefix,
            screen_checked_prefix=screen_checked_prefix,
        )

    def get_session_config(self, state: SessionState) -> dict[str, Any]:
        """Return a copy of the current session configuration."""
        return copy.deepcopy(state.meta)

    def get_check_screen_prefix(self, state: SessionState | None) -> str:
        """Resolve the check-screen prefix for the given session."""
        return resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)

    def get_screen_checked_prefix(self, state: SessionState | None) -> str:
        """Resolve the screen-checked prefix for the given session."""
        return resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)

    def get_session_duration(self, state: SessionState) -> float:
        """Return the elapsed time since the session was created."""
        return max(0.0, time.monotonic() - state.created_at)

    # ============================================================================
    # History helpers
    # ============================================================================

    def get_history_text(self, state: SessionState) -> str:
        return self._history.get_text(state)

    def get_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts (untrimmed)."""
        return self._history.get_user_texts(state)

    def get_tool_history_text(self, state: SessionState, *, max_tokens: int | None = None) -> str:
        """Get trimmed history tailored for the tool model."""
        return self._history.get_tool_history_text(state, max_tokens=max_tokens)

    def set_history_text(self, state: SessionState, history_text: str) -> str:
        return self._history.set_text(state, history_text)

    def set_history_turns(self, state: SessionState, turns: list[HistoryTurn]) -> str:
        """Set history from pre-parsed turns and apply import-time trimming."""
        return self._history.set_turns(state, turns)

    def get_history_turn_count(self, state: SessionState) -> int:
        """Get the number of history turns currently stored."""
        return len(state.history_turns)

    def append_user_utterance(self, state: SessionState, user_utt: str) -> str | None:
        normalized_user = strip_screen_prefix(
            user_utt or "",
            self.get_check_screen_prefix(state),
            self.get_screen_checked_prefix(state),
        )
        return self._history.append_user_turn(state, normalized_user)

    def append_history_turn(
        self, state: SessionState, user_utt: str, assistant_text: str, *, turn_id: str | None = None
    ) -> str:
        normalized_user = strip_screen_prefix(
            user_utt or "",
            self.get_check_screen_prefix(state),
            self.get_screen_checked_prefix(state),
        )
        return self._history.append_turn(state, normalized_user, assistant_text, turn_id=turn_id)

    # ============================================================================
    # Request/task tracking
    # ============================================================================

    def set_active_request(self, state: SessionState, request_id: str) -> None:
        state.active_request_id = request_id

    def is_request_cancelled(self, state: SessionState, request_id: str) -> bool:
        return _is_cancelled(state, request_id)

    def track_task(self, state: SessionState, task: asyncio.Task) -> None:
        state.task = task

        def _clear_task(completed: asyncio.Task) -> None:
            if state.task is completed:
                state.task = None

        task.add_done_callback(_clear_task)

    def has_running_task(self, state: SessionState) -> bool:
        return _has_running(state)

    def cancel_session_requests(self, state: SessionState) -> None:
        _cancel_requests(state)

    def cleanup_session_requests(self, state: SessionState) -> dict[str, str]:
        return _cleanup_requests(state)

    async def abort_session_requests(
        self,
        state: SessionState | None,
    ) -> dict[str, str]:
        """Cancel tracked requests and best-effort abort active engine work."""
        if not state:
            return {"active": ""}

        self.cancel_session_requests(state)
        request_info = self.cleanup_session_requests(state)

        active_request_id = request_info.get("active")
        if DEPLOY_CHAT and active_request_id and self._chat_engine is not None:
            with contextlib.suppress(Exception):
                await self._chat_engine.abort(active_request_id)

        return request_info

    # ============================================================================
    # Token budget helpers
    # ============================================================================

    def get_effective_user_utt_max_tokens(self, state: SessionState | None, *, for_followup: bool = False) -> int:
        """Get the effective max tokens for user utterance after accounting for prefix."""
        return get_effective_user_utt_max_tokens(state, for_followup=for_followup)


__all__ = ["SessionHandler"]
