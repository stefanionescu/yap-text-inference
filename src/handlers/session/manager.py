"""Session handler orchestration logic."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any
from .config import resolve_screen_prefix
from .time import format_session_timestamp
from src.state.session import SessionState
from ...tokens.prefix import strip_screen_prefix
from .history import HistoryController, HistoryRuntimeConfig, build_history_runtime_config
from src.config import (
    CHAT_MODEL,
    TOOL_MODEL,
    USER_UTT_MAX_TOKENS,
    DEFAULT_CHECK_SCREEN_PREFIX,
    DEFAULT_SCREEN_CHECKED_PREFIX,
)
from .requests import (
    attach_request_task,
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
        history_config: HistoryRuntimeConfig | None = None,
    ):
        self._chat_engine = chat_engine
        self._chat_tokenizer = chat_tokenizer
        self._tool_tokenizer = tool_tokenizer
        self._tool_history_budget = tool_history_budget
        self._history_config = history_config or build_history_runtime_config()
        self._history = HistoryController(
            config=self._history_config,
            tool_history_budget=tool_history_budget,
            chat_tokenizer=chat_tokenizer,
            tool_tokenizer=tool_tokenizer,
        )

    @property
    def history_config(self) -> HistoryRuntimeConfig:
        """Get the runtime history configuration used by this handler."""
        return self._history_config

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
                "chat_model": CHAT_MODEL if self._history_config.deploy_chat else None,
                "tool_model": TOOL_MODEL if self._history_config.deploy_tool else None,
                "check_screen_prefix": None,
                "screen_checked_prefix": None,
            }
        )
        # Cache default prefix token counts
        state.check_screen_prefix_tokens = self._count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        state.screen_checked_prefix_tokens = self._count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
        state.screen_followup_pending = False
        return meta

    def set_screen_followup_pending(self, state: SessionState | None, pending: bool) -> None:
        """Mark whether the next message turn should use screen_checked_prefix."""
        if state is None:
            return
        state.screen_followup_pending = bool(pending)

    def append_user_utterance(
        self,
        state: SessionState,
        chat_user_utt: str,
        *,
        tool_user_utt: str | None = None,
    ) -> str | None:
        check_screen_prefix = resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)
        screen_checked_prefix = resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)
        normalized_user = strip_screen_prefix(
            chat_user_utt or "",
            check_screen_prefix,
            screen_checked_prefix,
        )
        normalized_tool_user = (
            strip_screen_prefix(
                tool_user_utt or "",
                check_screen_prefix,
                screen_checked_prefix,
            )
            if tool_user_utt is not None
            else None
        )
        return self._history.append_user_turn(state, normalized_user, tool_user_utt=normalized_tool_user)

    def append_history_turn(
        self, state: SessionState, chat_user_utt: str, assistant_text: str, *, turn_id: str | None = None
    ) -> str:
        check_screen_prefix = resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)
        screen_checked_prefix = resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)
        normalized_user = strip_screen_prefix(
            chat_user_utt or "",
            check_screen_prefix,
            screen_checked_prefix,
        )
        return self._history.append_turn(state, normalized_user, assistant_text, turn_id=turn_id)

    # ============================================================================
    # Request/task tracking
    # ============================================================================

    async def begin_request(self, state: SessionState, request_id: str) -> bool:
        """Transition session into running state for the given request."""
        async with state.request_lock:
            return begin_session_request(state, request_id)

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

    def get_effective_chat_user_utt_max_tokens(self, state: SessionState | None, *, for_followup: bool = False) -> int:
        """Get the effective max tokens for chat user utterance after accounting for prefix."""
        if state is None:
            prefix = DEFAULT_SCREEN_CHECKED_PREFIX if for_followup else DEFAULT_CHECK_SCREEN_PREFIX
            return max(1, USER_UTT_MAX_TOKENS - self._count_prefix_tokens(prefix))
        prefix_tokens = state.screen_checked_prefix_tokens if for_followup else state.check_screen_prefix_tokens
        return max(1, USER_UTT_MAX_TOKENS - prefix_tokens)

    def trim_chat_user_utterance(self, chat_user_utt: str, max_tokens: int) -> str:
        """Trim a chat user utterance using chat-side tokenizer semantics."""
        text = chat_user_utt or ""
        if max_tokens <= 0 or not text:
            return ""
        if self._history_config.deploy_chat and self._chat_tokenizer is not None:
            return self._chat_tokenizer.trim(text, max_tokens=max_tokens, keep="start")
        if self._history_config.deploy_tool and self._tool_tokenizer is not None:
            return self._tool_tokenizer.trim(text, max_tokens=max_tokens, keep="start")
        return text

    def get_effective_tool_user_utt_max_tokens(self) -> int:
        """Get max tokens allowed for tool-side user utterance trimming."""
        if self._tool_history_budget is not None:
            return max(1, int(self._tool_history_budget))
        return max(1, USER_UTT_MAX_TOKENS)

    def trim_tool_user_utterance(self, tool_user_utt: str, max_tokens: int) -> str:
        """Trim a user utterance using the tool tokenizer semantics."""
        text = tool_user_utt or ""
        if max_tokens <= 0 or not text:
            return ""
        if self._tool_tokenizer is not None:
            return self._tool_tokenizer.trim(text, max_tokens=max_tokens, keep="end")
        return text

    def count_chat_tokens(self, text: str) -> int:
        """Count chat tokens using the configured runtime chat tokenizer."""
        if self._chat_tokenizer is None:
            raise RuntimeError("Chat tokenizer is not configured")
        return self._chat_tokenizer.count(text)

    def _count_prefix_tokens(self, prefix: str | None) -> int:
        if not prefix or not self._history_config.deploy_chat or self._chat_tokenizer is None:
            return 0
        return self._chat_tokenizer.count(f"{prefix.strip()} ")


__all__ = ["SessionHandler"]
