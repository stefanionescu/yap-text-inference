"""Session handler orchestration logic."""

from __future__ import annotations

import asyncio
import copy
import time
from typing import Any

from src.config import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL
from src.utils import RateLimitError, SlidingWindowRateLimiter, format_session_timestamp

from .history import HistoryController
from .state import SessionState, SESSION_IDLE_TTL_SECONDS


class SessionHandler:
    """Handles session metadata, request tracking, and lifecycle."""

    CANCELLED_SENTINEL = "__CANCELLED__"

    def __init__(self, idle_ttl_seconds: int = SESSION_IDLE_TTL_SECONDS):
        self._sessions: dict[str, SessionState] = {}
        self._idle_ttl_seconds = idle_ttl_seconds
        self._history = HistoryController()

    def _get_state(self, session_id: str) -> SessionState | None:
        return self._sessions.get(session_id)

    def _ensure_state(self, session_id: str) -> SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        else:
            state.touch()
        return state

    # ------------------------------------------------------------------ #
    # Session metadata / lifecycle
    # ------------------------------------------------------------------ #
    def initialize_session(self, session_id: str) -> dict[str, Any]:
        """Ensure a session state exists and return its metadata."""

        self._evict_idle_sessions()
        state = self._sessions.get(session_id)
        if state:
            state.touch()
            return state.meta

        now_str = format_session_timestamp()
        meta = {
            "now_str": now_str,
            "chat_gender": None,
            "chat_personality": None,
            "chat_prompt": None,
            "tool_prompt": None,
            "chat_sampling": None,
            "chat_model": CHAT_MODEL if DEPLOY_CHAT else None,
            "tool_model": TOOL_MODEL if DEPLOY_TOOL else None,
        }
        new_state = SessionState(session_id=session_id, meta=meta)
        self._sessions[session_id] = new_state
        new_state.touch()
        return meta

    def update_session_config(
        self,
        session_id: str,
        chat_gender: str | None = None,
        chat_personality: str | None = None,
        chat_prompt: str | None = None,
        tool_prompt: str | None = None,
        chat_sampling: dict[str, Any] | None = None,
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

        if tool_prompt is not None:
            tp = tool_prompt or None
            meta["tool_prompt"] = tp
            changed["tool_prompt"] = bool(tp)

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

    def clear_session_state(self, session_id: str) -> None:
        """Drop all in-memory data for a session."""

        state = self._sessions.pop(session_id, None)
        if state and state.task and not state.task.done():
            state.task.cancel()

    # ------------------------------------------------------------------ #
    # History helpers
    # ------------------------------------------------------------------ #
    def get_history_text(self, session_id: str) -> str:
        state = self._get_state(session_id)
        if not state:
            return ""
        state.touch()
        return self._history.get_text(state)

    def set_history_text(self, session_id: str, history_text: str) -> str:
        state = self._ensure_state(session_id)
        rendered = self._history.set_text(state, history_text)
        state.touch()
        return rendered

    def append_user_utterance(self, session_id: str, user_utt: str) -> str | None:
        state = self._ensure_state(session_id)
        turn_id = self._history.append_user_turn(state, user_utt)
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
        rendered = self._history.append_turn(
            state,
            user_utt,
            assistant_text,
            turn_id=turn_id,
        )
        state.touch()
        return rendered

    # ------------------------------------------------------------------ #
    # Request/task tracking
    # ------------------------------------------------------------------ #
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

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
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
            from src.engines import get_chat_engine  # local import to avoid cycles

            await (await get_chat_engine()).abort_request(req_info["active"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if DEPLOY_TOOL and req_info.get("tool"):
        try:
            from src.engines import get_tool_engine  # local import to avoid cycles

            await (await get_tool_engine()).abort_request(req_info["tool"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if clear_state:
        session_handler.clear_session_state(session_id)

    return req_info


