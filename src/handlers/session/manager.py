"""Session handler orchestration logic."""

from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any
from .config import resolve_screen_prefix
from .time import format_session_timestamp
from ...tokens.prefix import strip_screen_prefix
from src.state.session import ChatMessage, HistoryTurn, SessionState
from src.execution.tool.prompt_budget import fit_tool_input_to_budget
from src.execution.chat.prompt_budget import fit_chat_prompt_to_budget
from .history import HistoryController, HistoryRuntimeConfig, build_history_runtime_config
from src.config import CHAT_MODEL, TOOL_MODEL, CHAT_MAX_LEN, DEFAULT_CHECK_SCREEN_PREFIX, DEFAULT_SCREEN_CHECKED_PREFIX
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
        tool_input_budget: int | None = None,
        chat_tokenizer: FastTokenizer | None = None,
        tool_tokenizer: FastTokenizer | None = None,
        history_config: HistoryRuntimeConfig | None = None,
    ):
        self._chat_engine = chat_engine
        self._chat_tokenizer = chat_tokenizer
        self._tool_tokenizer = tool_tokenizer
        self._tool_history_budget = tool_history_budget
        self._tool_input_budget = tool_input_budget if tool_input_budget is not None else tool_history_budget
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
        state.check_screen_prefix_tokens = self.count_prefix_tokens(DEFAULT_CHECK_SCREEN_PREFIX)
        state.screen_checked_prefix_tokens = self.count_prefix_tokens(DEFAULT_SCREEN_CHECKED_PREFIX)
        state.screen_followup_pending = False
        return meta

    def set_screen_followup_pending(self, state: SessionState | None, pending: bool) -> None:
        """Mark whether the next message turn should use screen_checked_prefix."""
        if state is None:
            return
        state.screen_followup_pending = bool(pending)

    def normalize_user_utterances(
        self,
        state: SessionState,
        chat_user_utt: str,
        *,
        tool_user_utt: str | None = None,
    ) -> tuple[str, str | None]:
        """Strip internal screen prefixes from chat/tool user variants."""
        check_screen_prefix = resolve_screen_prefix(state, DEFAULT_CHECK_SCREEN_PREFIX, is_checked=False)
        screen_checked_prefix = resolve_screen_prefix(state, DEFAULT_SCREEN_CHECKED_PREFIX, is_checked=True)
        normalized_chat = strip_screen_prefix(
            chat_user_utt or "",
            check_screen_prefix,
            screen_checked_prefix,
        )
        normalized_tool = (
            strip_screen_prefix(
                tool_user_utt or "",
                check_screen_prefix,
                screen_checked_prefix,
            )
            if tool_user_utt is not None
            else None
        )
        return normalized_chat, normalized_tool

    def reserve_history_turn_id(
        self,
        state: SessionState,
        chat_user_utt: str,
        *,
        tool_user_utt: str | None = None,
    ) -> str | None:
        """Reserve a stable tool-history id without mutating either history store."""
        normalized_chat, normalized_tool = self.normalize_user_utterances(
            state,
            chat_user_utt,
            tool_user_utt=tool_user_utt,
        )
        return self._history.reserve_turn_id(
            chat_user_utt=normalized_chat,
            tool_user_utt=normalized_tool,
        )

    def prepare_tool_turn(
        self,
        state: SessionState,
        tool_user_utt: str,
        *,
        turn_id: str | None = None,
    ) -> tuple[str, str]:
        """Fit/store the tool-side user text exactly once and return prior fitted history."""
        normalized_chat, normalized_tool = self.normalize_user_utterances(
            state,
            tool_user_utt,
            tool_user_utt=tool_user_utt,
        )
        tool_user = normalized_tool if normalized_tool is not None else normalized_chat
        prompt_fit = fit_tool_input_to_budget(
            self._history.get_tool_user_texts(state),
            tool_user,
            self._tool_tokenizer,
            max_input_tokens=self._resolve_tool_input_budget(),
        )
        if prompt_fit.tool_user_utt:
            self._history.append_tool_turn(state, prompt_fit.tool_user_utt, turn_id=turn_id)
        return prompt_fit.tool_user_utt, prompt_fit.tool_user_history

    def append_chat_turn(
        self, state: SessionState, chat_user_utt: str, assistant_text: str, *, turn_id: str | None = None
    ) -> str:
        normalized_user, _ = self.normalize_user_utterances(state, chat_user_utt)
        _ = turn_id
        return self._history.append_chat_response(state, normalized_user, assistant_text)

    def fit_start_chat_history(
        self,
        state: SessionState,
        *,
        static_prefix: str,
        runtime_text: str = "",
    ) -> list[ChatMessage]:
        """Exact-fit seeded chat history at start time and reject impossible latest turns."""
        if not self._history_config.deploy_chat:
            return []
        if self._chat_tokenizer is None:
            raise RuntimeError("Chat tokenizer is not configured")

        original_history = self._history.get_chat_messages(state)
        if not original_history:
            return []

        prompt_fit = fit_chat_prompt_to_budget(
            static_prefix,
            runtime_text,
            original_history,
            "",
            self._chat_tokenizer,
            max_prompt_tokens=CHAT_MAX_LEN,
        )
        if prompt_fit.history_messages:
            self._history.set_exact_chat_messages(state, prompt_fit.history_messages)
            return prompt_fit.history_messages

        raise ValueError("seed history exceeds exact context budget at session start")

    # ============================================================================
    # History accessors
    # ============================================================================

    def get_chat_messages(self, state: SessionState) -> list[ChatMessage]:
        """Get a copy of committed chat history messages."""
        return self._history.get_chat_messages(state)

    def set_mode_histories(
        self,
        state: SessionState,
        *,
        chat_messages: list[ChatMessage] | None = None,
        tool_turns: list[HistoryTurn] | None = None,
    ) -> str:
        """Set imported chat/tool stores and apply import-time trimming."""
        return self._history.set_mode_histories(
            state,
            chat_messages=chat_messages,
            tool_turns=tool_turns,
        )

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
    # Token helpers
    # ============================================================================

    def count_chat_tokens(self, text: str) -> int:
        """Count chat tokens using the configured runtime chat tokenizer."""
        if self._chat_tokenizer is None:
            raise RuntimeError("Chat tokenizer is not configured")
        return self._chat_tokenizer.count(text)

    def count_prefix_tokens(self, prefix: str | None) -> int:
        """Count prefix tokens using the configured runtime chat tokenizer."""
        if not prefix or not self._history_config.deploy_chat or self._chat_tokenizer is None:
            return 0
        return self._chat_tokenizer.count(f"{prefix.strip()} ")

    def _resolve_tool_input_budget(self) -> int:
        if self._tool_input_budget is not None:
            return max(1, int(self._tool_input_budget))
        if self._tool_history_budget is not None:
            return max(1, int(self._tool_history_budget))
        return 1


__all__ = ["SessionHandler"]
