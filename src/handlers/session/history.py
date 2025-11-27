"""History parsing/rendering utilities for session handling."""

from __future__ import annotations

import uuid

from src.config import DEPLOY_CHAT, HISTORY_MAX_TOKENS
from src.tokens import count_tokens_chat
from src.utils.sanitize import sanitize_llm_output

from .state import HistoryTurn, SessionState


def render_history(turns: list[HistoryTurn]) -> str:
    """Render history turns to a simple text transcript."""

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


def parse_history_text(history_text: str) -> list[HistoryTurn]:
    """Parse a transcript back into structured turns."""

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
        turns.append(
            HistoryTurn(turn_id=uuid.uuid4().hex, user=user_text, assistant=assistant_text)
        )
        current_user = []
        current_assistant = []
        mode = None

    for line in text.splitlines():
        if line.startswith("User:"):
            _flush()
            current_user = [line[len("User:") :].lstrip()]
            current_assistant = []
            mode = "user"
        elif line.startswith("Assistant:"):
            current_assistant = [line[len("Assistant:") :].lstrip()]
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


def trim_history_turns(state: SessionState) -> None:
    """Trim history to stay within token budget."""

    if not state.history_turns or not DEPLOY_CHAT:
        return

    rendered = render_history(state.history_turns)
    if not rendered:
        state.history_turns = []
        return

    tokens = count_tokens_chat(rendered)
    if tokens <= HISTORY_MAX_TOKENS:
        return

    while state.history_turns and tokens > HISTORY_MAX_TOKENS:
        state.history_turns.pop(0)
        rendered = render_history(state.history_turns)
        tokens = count_tokens_chat(rendered) if rendered else 0


class HistoryController:
    """Encapsulates history CRUD operations for SessionState instances."""

    def get_text(self, state: SessionState) -> str:
        trim_history_turns(state)
        return render_history(state.history_turns)

    def set_text(self, state: SessionState, history_text: str) -> str:
        state.history_turns = parse_history_text(history_text)
        trim_history_turns(state)
        return render_history(state.history_turns)

    def append_user_turn(self, state: SessionState, user_utt: str) -> str | None:
        user = (user_utt or "").strip()
        if not user:
            return None
        turn_id = uuid.uuid4().hex
        state.history_turns.append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
        trim_history_turns(state)
        return turn_id

    def append_turn(
        self,
        state: SessionState,
        user_utt: str,
        assistant_text: str,
        *,
        turn_id: str | None = None,
    ) -> str:
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
                return render_history(state.history_turns)
            fallback_turn = HistoryTurn(turn_id=uuid.uuid4().hex, user=user, assistant=assistant)
            state.history_turns.append(fallback_turn)

        trim_history_turns(state)
        return render_history(state.history_turns)


