"""Session handler for WebSocket connections."""

from __future__ import annotations

import asyncio
import copy
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..config import CHAT_MODEL, TOOL_MODEL, HISTORY_MAX_TOKENS, DEPLOY_CHAT, DEPLOY_TOOL
from ..tokens import count_tokens_chat
from ..utils.sanitize import sanitize_llm_output
from ..utils.time import format_session_timestamp


SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "1800"))


@dataclass
class HistoryTurn:
    turn_id: str
    user: str
    assistant: str


@dataclass
class SessionState:
    """Container for all mutable session-scoped data."""

    session_id: str
    meta: dict[str, Any]
    history_turns: list[HistoryTurn] = field(default_factory=list)
    task: asyncio.Task | None = None
    active_request_id: str | None = None
    tool_request_id: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)
    chat_prompt_last_update_at: float = 0.0

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

    def get_chat_prompt_last_update_at(self, session_id: str) -> float:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.touch()
        return float(state.chat_prompt_last_update_at or 0.0)

    def set_chat_prompt_last_update_at(self, session_id: str, timestamp: float) -> None:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.chat_prompt_last_update_at = timestamp
        state.touch()

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
        self._trim_history_turns(state)
        return self._render_history(state.history_turns)

    def set_history_text(self, session_id: str, history_text: str) -> str:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        state.history_turns = self._parse_history_text(history_text)
        self._trim_history_turns(state)
        state.touch()
        return self._render_history(state.history_turns)

    def append_user_utterance(self, session_id: str, user_utt: str) -> str | None:
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        user = (user_utt or "").strip()
        if not user:
            return None

        turn_id = uuid.uuid4().hex
        state.history_turns.append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
        self._trim_history_turns(state)
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
        state = self._sessions.get(session_id)
        if not state:
            self.initialize_session(session_id)
            state = self._sessions[session_id]
        user = (user_utt or "").strip()
        assistant_raw = assistant_text or ""
        assistant = sanitize_llm_output(assistant_raw) if assistant_raw else ""

        target_turn: HistoryTurn | None = None
        if turn_id:
            target_turn = next((turn for turn in state.history_turns if turn.turn_id == turn_id), None)

        if target_turn:
            if assistant:
                target_turn.assistant = assistant
        else:
            if not user and not assistant:
                return self._render_history(state.history_turns)
            fallback_turn = HistoryTurn(turn_id=uuid.uuid4().hex, user=user, assistant=assistant)
            state.history_turns.append(fallback_turn)

        self._trim_history_turns(state)
        state.touch()
        return self._render_history(state.history_turns)

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
    def _render_history(self, turns: list[HistoryTurn]) -> str:
        if not turns:
            return ""
        chunks: list[str] = []
        for turn in turns:
            lines: list[str] = []
            user_text = (turn.user or "").strip()
            assistant_text = (turn.assistant or "").strip()
            lines.append(f"User: {user_text}")
            if assistant_text:
                lines.append(f"Assistant: {assistant_text}")
            chunk = "\n".join(lines).strip()
            if chunk:
                chunks.append(chunk)
        return "\n\n".join(chunks)

    def _parse_history_text(self, history_text: str) -> list[HistoryTurn]:
        text = (history_text or "").strip()
        if not text:
            return []

        turns: list[HistoryTurn] = []
        current_user: list[str] = []
        current_assistant: list[str] = []
        mode: str | None = None

        def _flush() -> None:
            nonlocal current_user, current_assistant, mode
            if not current_user and not current_assistant:
                return
            user_text = "\n".join(current_user).strip()
            assistant_text = "\n".join(current_assistant).strip()
            turns.append(HistoryTurn(turn_id=uuid.uuid4().hex, user=user_text, assistant=assistant_text))
            current_user = []
            current_assistant = []
            mode = None

        for line in text.splitlines():
            if line.startswith("User:"):
                _flush()
                current_user = [line[len("User:"):].lstrip()]
                current_assistant = []
                mode = "user"
            elif line.startswith("Assistant:"):
                current_assistant = [line[len("Assistant:"):].lstrip()]
                mode = "assistant"
            else:
                if mode == "assistant":
                    current_assistant.append(line)
                elif mode == "user":
                    current_user.append(line)
                elif line.strip():
                    current_user.append(line)
                    mode = "user"

        _flush()
        return turns

    def _trim_history_turns(self, state: SessionState) -> None:
        if not state.history_turns or not DEPLOY_CHAT:
            return

        rendered = self._render_history(state.history_turns)
        if not rendered:
            state.history_turns = []
            return

        tokens = count_tokens_chat(rendered)
        if tokens <= HISTORY_MAX_TOKENS:
            return

        while state.history_turns and tokens > HISTORY_MAX_TOKENS:
            state.history_turns.pop(0)
            rendered = self._render_history(state.history_turns)
            tokens = count_tokens_chat(rendered) if rendered else 0

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


