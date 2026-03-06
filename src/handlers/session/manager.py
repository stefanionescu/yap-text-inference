"""Session handler orchestration logic."""

from __future__ import annotations

import copy
import time
import asyncio
import contextlib
from typing import TYPE_CHECKING, Any
from .history import HistoryController
from .time import format_session_timestamp
from ...tokens.prefix import strip_screen_prefix
from src.state.session import HistoryTurn, SessionState
from .config import resolve_screen_prefix, update_session_config as _update_config
from src.config import (
    CHAT_MODEL,
    TOOL_MODEL,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    USER_UTT_MAX_TOKENS,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
)
from .requests import (
    has_running_task,
    attach_request_task,
    is_request_cancelled,
    begin_session_request,
    close_session_requests,
    cancel_session_requests,
    cleanup_session_requests,
)

if TYPE_CHECKING:
    from src.engines.base import BaseEngine
    from src.tokens.tokenizer import FastTokenizer


class SessionHandler:
    """Stateless helper for session metadata, request tracking, and lifecycle.

    Methods operate on a SessionState passed by the caller (per-connection).
    No internal session dict or eviction logic — the connection IS the session.
    """

    def __init__(
        self,
        *,
        chat_engine: BaseEngine | None = None,
        tool_history_budget: int | None = None,
        chat_tokenizer: FastTokenizer | None = None,
        tool_tokenizer: FastTokenizer | None = None,
    ):
        self._chat_engine = chat_engine
        self._chat_tokenizer = chat_tokenizer
        self._tool_tokenizer = tool_tokenizer
        self._history = HistoryController(
            tool_history_budget=tool_history_budget,
            chat_tokenizer=chat_tokenizer,
            tool_tokenizer=tool_tokenizer,
        )

    # ============================================================================
    # Session metadata / lifecycle
    # ============================================================================

    def initialize_session(self, state: SessionState) -> dict[str, Any]:
        """Populate a fresh session state with default metadata."""
        self._history.initialize_mode_state(state)
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
        state.check_screen_prefix_tokens = self._count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        state.screen_checked_prefix_tokens = self._count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
        state.screen_followup_pending = False
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
            count_prefix_tokens_fn=self._count_prefix_tokens,
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

    def has_screen_followup_pending(self, state: SessionState | None) -> bool:
        """Return whether next turn should use the screen-checked prefix."""
        return bool(state and state.screen_followup_pending)

    def set_screen_followup_pending(self, state: SessionState | None, pending: bool) -> None:
        """Mark whether the next message turn should use screen_checked_prefix."""
        if state is None:
            return
        state.screen_followup_pending = bool(pending)

    # ============================================================================
    # History helpers
    # ============================================================================

    def get_history_text(self, state: SessionState) -> str:
        return self._history.get_text(state)

    def get_history_turns(self, state: SessionState) -> list[HistoryTurn]:
        """Get structured conversation turns for prompt construction."""
        return self._history.get_turns(state)

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
        if state.history_turns is not None:
            return len(state.history_turns)
        if state.tool_history_turns is not None:
            return len(state.tool_history_turns)
        return 0

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

    async def begin_request(self, state: SessionState, request_id: str) -> bool:
        """Transition session into running state for the given request."""
        async with state.request_lock:
            return begin_session_request(state, request_id)

    def is_request_cancelled(self, state: SessionState, request_id: str) -> bool:
        return is_request_cancelled(state, request_id)

    async def track_request_task(
        self,
        state: SessionState,
        *,
        request_id: str,
        task: asyncio.Task,
    ) -> None:
        """Bind a task handle to a specific active request."""
        async with state.request_lock:
            attach_request_task(state, request_id=request_id, task=task)

    def has_running_task(self, state: SessionState) -> bool:
        return has_running_task(state)

    async def cancel_session_requests(self, state: SessionState) -> None:
        async with state.request_lock:
            cancel_session_requests(state)

    async def cleanup_session_requests(
        self,
        state: SessionState,
        *,
        request_id: str | None = None,
        force: bool = False,
    ) -> dict[str, str]:
        async with state.request_lock:
            return cleanup_session_requests(
                state,
                request_id=request_id,
                force=force,
            )

    async def complete_request(self, state: SessionState, request_id: str) -> None:
        """Finalize request lifecycle if this request is still active."""
        await self.cleanup_session_requests(state, request_id=request_id, force=False)

    async def mark_session_closed(self, state: SessionState) -> None:
        """Mark a session as closed and clear in-flight request pointers."""
        async with state.request_lock:
            close_session_requests(state)

    async def abort_session_requests(
        self,
        state: SessionState | None,
    ) -> dict[str, str]:
        """Cancel tracked requests and best-effort abort active engine work."""
        if not state:
            return {"active": ""}

        active_request_id = state.active_request_id or ""
        await self.cancel_session_requests(state)
        if active_request_id and self._chat_engine is not None:
            with contextlib.suppress(Exception):
                await self._chat_engine.abort(active_request_id)

        return await self.cleanup_session_requests(state, force=True)

    # ============================================================================
    # Token budget helpers
    # ============================================================================

    def get_effective_user_utt_max_tokens(self, state: SessionState | None, *, for_followup: bool = False) -> int:
        """Get the effective max tokens for user utterance after accounting for prefix."""
        if state is None:
            prefix = DEFAULT_SCREEN_CHECKED_PREFIX if for_followup else DEFAULT_CHECK_SCREEN_PREFIX
            return max(1, USER_UTT_MAX_TOKENS - self._count_prefix_tokens(prefix))
        prefix_tokens = state.screen_checked_prefix_tokens if for_followup else state.check_screen_prefix_tokens
        return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

    def trim_user_utterance(self, user_utt: str, max_tokens: int) -> str:
        """Trim a user utterance using the active deployment tokenizer."""
        text = user_utt or ""
        if max_tokens <= 0 or not text:
            return ""
        if DEPLOY_CHAT and self._chat_tokenizer is not None:
            return self._chat_tokenizer.trim(text, max_tokens=max_tokens, keep="start")
        if DEPLOY_TOOL and self._tool_tokenizer is not None:
            return self._tool_tokenizer.trim(text, max_tokens=max_tokens, keep="start")
        return text

    def count_chat_tokens(self, text: str) -> int:
        """Count chat tokens using the configured runtime chat tokenizer."""
        if self._chat_tokenizer is None:
            raise RuntimeError("Chat tokenizer is not configured")
        return self._chat_tokenizer.count(text)

    def _count_prefix_tokens(self, prefix: str | None) -> int:
        if not prefix or not DEPLOY_CHAT or self._chat_tokenizer is None:
            return 0
        return self._chat_tokenizer.count(f"{prefix.strip()} ")


__all__ = ["SessionHandler"]
