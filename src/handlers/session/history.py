"""History parsing/rendering utilities for session handling."""

from __future__ import annotations

import uuid
from typing import List

from src.config import DEPLOY_CHAT, HISTORY_MAX_TOKENS
from src.tokens import count_tokens_chat

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


