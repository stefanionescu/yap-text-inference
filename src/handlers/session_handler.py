"""Session handler for WebSocket connections."""

from __future__ import annotations

import asyncio
import copy
import os
import time
from dataclasses import dataclass, field
from typing import Any

from ..config import CHAT_MODEL, TOOL_MODEL, HISTORY_MAX_TOKENS, DEPLOY_CHAT, DEPLOY_TOOL
from ..tokens import count_tokens_chat, trim_history_preserve_messages_chat
from ..utils.time_utils import format_session_timestamp


SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "1800"))


@dataclass
class SessionState:
    """Container for all mutable session-scoped data."""

    session_id: str
    meta: dict[str, Any]
    history: str = ""
    task: asyncio.Task | None = None
    active_request_id: str | None = None
    tool_request_id: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        self.last_access = time.monotonic()


class SessionHandler:
    """Handles session metadata, request tracking, and lifecycle."""

    CANCELLED_SENTINEL = "__CANCELLED__"

    def __init__(self, idle_ttl_seconds: int = SESSION_IDLE_TTL_SECONDS):
        self._sessions: dict[str, SessionState] = {}
        self._idle_ttl_seconds = idle_ttl_seconds

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
        meta = self.initialize_session(session_id)
        state = self._sessions[session_id]
        state.touch()

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
            changed["chat_sampling"] = sampling_copy.copy() if isinstance(sampling_copy, dict) else None

        return changed

    def get_session_config(self, session_id: str) -> dict[str, Any]:
        """Return a copy of the current session configuration."""
        state = self._sessions.get(session_id)
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
        state = self._sessions.get(session_id)
        if not state:
            return ""
        state.touch()
        return state.history

    def set_history_text(self, session_id: str, history_text: str) -> str:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        normalized = self._normalize_history(history_text)
        state.history = normalized
        state.touch()
        return normalized

    def append_history_turn(self, session_id: str, user_utt: str, assistant_text: str) -> str:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        turn = self._format_turn(user_utt, assistant_text)
        if not turn:
            return state.history

        combined = f"{state.history}\n\n{turn}".strip() if state.history.strip() else turn
        normalized = self._normalize_history(combined)
        state.history = normalized
        state.touch()
        return normalized

    # ------------------------------------------------------------------ #
    # Request/task tracking
    # ------------------------------------------------------------------ #
    def set_active_request(self, session_id: str, request_id: str) -> None:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.active_request_id = request_id
        state.touch()

    def set_tool_request(self, session_id: str, request_id: str) -> None:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.tool_request_id = request_id
        state.touch()

    def get_tool_request_id(self, session_id: str) -> str:
        state = self._sessions.get(session_id)
        return state.tool_request_id or "" if state else ""

    def clear_tool_request_id(self, session_id: str) -> None:
        state = self._sessions.get(session_id)
        if state:
            state.tool_request_id = None

    def is_request_cancelled(self, session_id: str, request_id: str) -> bool:
        state = self._sessions.get(session_id)
        if not state:
            return True
        active = state.active_request_id
        if active == self.CANCELLED_SENTINEL:
            return True
        if not active:
            return False
        return active != request_id

    def track_task(self, session_id: str, task: asyncio.Task) -> None:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.task = task
        state.touch()

        def _clear_task(completed: asyncio.Task) -> None:
            current = self._sessions.get(session_id)
            if current and current.task is completed:
                current.task = None
                current.touch()

        task.add_done_callback(_clear_task)

    def has_running_task(self, session_id: str) -> bool:
        state = self._sessions.get(session_id)
        return bool(state and state.task and not state.task.done())

    def cancel_session_requests(self, session_id: str) -> None:
        state = self._sessions.get(session_id)
        if not state:
            return
        state.active_request_id = self.CANCELLED_SENTINEL
        if state.task and not state.task.done():
            state.task.cancel()

    def cleanup_session_requests(self, session_id: str) -> dict[str, str]:
        state = self._sessions.get(session_id)
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
    def _normalize_history(self, history_text: str) -> str:
        text = (history_text or "").strip()
        if not text:
            return ""
        if DEPLOY_CHAT and count_tokens_chat(text) > HISTORY_MAX_TOKENS:
            text = trim_history_preserve_messages_chat(text, HISTORY_MAX_TOKENS)
        return text

    @staticmethod
    def _format_turn(user_utt: str, assistant_text: str) -> str:
        user = (user_utt or "").strip()
        assistant = (assistant_text or "").strip()
        if not user and not assistant:
            return ""
        return f"User: {user}\nAssistant: {assistant}".strip()

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


# Global session handler instance
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
            from ..engines import get_chat_engine  # local import to avoid cycles

            await (await get_chat_engine()).abort_request(req_info["active"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if DEPLOY_TOOL and req_info.get("tool"):
        try:
            from ..engines import get_tool_engine  # local import to avoid cycles

            await (await get_tool_engine()).abort_request(req_info["tool"])
        except Exception:  # noqa: BLE001 - best effort
            pass

    if clear_state:
        session_handler.clear_session_state(session_id)

    return req_info


