"""History parsing/rendering utilities for session handling."""

from __future__ import annotations

import uuid

from src.config import (
    CLASSIFIER_HISTORY_TOKENS,
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    HISTORY_MAX_TOKENS,
)
from src.tokens import build_user_history_for_tool, count_tokens_chat

from .state import HistoryTurn, SessionState


def render_history(turns: list[HistoryTurn]) -> str:
    """Render history turns to text: 'User: X\\nAssistant: Y'"""
    if not turns:
        return ""
    chunks: list[str] = []
    for turn in turns:
        user_text = (turn.user or "").strip()
        assistant_text = (turn.assistant or "").strip()
        lines = [f"User: {user_text}"]
        if assistant_text:
            lines.append(f"Assistant: {assistant_text}")
        chunk = "\n".join(lines).strip()
        if chunk:
            chunks.append(chunk)
    return "\n\n".join(chunks)


def parse_history_text(history_text: str) -> list[HistoryTurn]:
    """Parse text transcript back into structured turns."""
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
        turns.append(HistoryTurn(
            turn_id=uuid.uuid4().hex,
            user="\n".join(current_user).strip(),
            assistant="\n".join(current_assistant).strip(),
        ))
        current_user, current_assistant, mode = [], [], None

    for line in text.splitlines():
        if line.startswith("User:"):
            _flush()
            current_user = [line[5:].lstrip()]
            mode = "user"
        elif line.startswith("Assistant:"):
            current_assistant = [line[10:].lstrip()]
            mode = "assistant"
        elif mode == "assistant":
            current_assistant.append(line)
        elif mode == "user":
            current_user.append(line)
        elif line.strip():
            current_user.append(line)
            mode = "user"
    _flush()
    return turns


def trim_history(state: SessionState) -> None:
    """Trim history by HISTORY_MAX_TOKENS when chat is deployed.
    
    When classifier-only, no trimming is done here - the classifier adapter
    handles its own trimming using its own tokenizer.
    """
    if not state.history_turns:
        return
    
    # Skip if chat model is not deployed (classifier handles its own trimming)
    if not DEPLOY_CHAT:
        return
    
    rendered = render_history(state.history_turns)
    if not rendered:
        state.history_turns = []
        return
    
    tokens = count_tokens_chat(rendered)
    while state.history_turns and tokens > HISTORY_MAX_TOKENS:
        state.history_turns.pop(0)
        rendered = render_history(state.history_turns)
        tokens = count_tokens_chat(rendered) if rendered else 0


def render_tool_history_text(turns: list[HistoryTurn]) -> str:
    """Render user-only history trimmed for the classifier/tool model."""
    if not DEPLOY_TOOL:
        return ""
    user_texts = get_user_texts(turns)
    if not user_texts:
        return ""
    return build_user_history_for_tool(
        user_texts,
        CLASSIFIER_HISTORY_TOKENS,
        prefix="USER",
    )


def get_user_texts(turns: list[HistoryTurn]) -> list[str]:
    """Extract raw user texts from history turns.
    
    Returns list of user utterances (most recent last).
    Trimming is handled by the classifier adapter using its own tokenizer.
    """
    if not turns:
        return []
    return [turn.user.strip() for turn in turns if turn.user and turn.user.strip()]


class HistoryController:
    """History operations for SessionState."""

    def get_text(self, state: SessionState) -> str:
        """Get full history (User + Assistant)."""
        trim_history(state)
        return render_history(state.history_turns)
    
    def get_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts (no trimming)."""
        trim_history(state)
        return get_user_texts(state.history_turns)

    def get_tool_history_text(self, state: SessionState) -> str:
        """Get trimmed user-only history for the classifier/tool model."""
        trim_history(state)
        return render_tool_history_text(state.history_turns)

    def set_text(self, state: SessionState, history_text: str) -> str:
        state.history_turns = parse_history_text(history_text)
        trim_history(state)
        return render_history(state.history_turns)

    def append_user_turn(self, state: SessionState, user_utt: str) -> str | None:
        user = (user_utt or "").strip()
        if not user:
            return None
        turn_id = uuid.uuid4().hex
        state.history_turns.append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
        trim_history(state)
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
        assistant = assistant_text or ""

        if turn_id:
            target = next((t for t in state.history_turns if t.turn_id == turn_id), None)
            if target and assistant:
                target.assistant = assistant
                trim_history(state)
                return render_history(state.history_turns)

        if not user and not assistant:
            return render_history(state.history_turns)
        
        state.history_turns.append(HistoryTurn(
            turn_id=turn_id or uuid.uuid4().hex,
            user=user,
            assistant=assistant,
        ))
        trim_history(state)
        return render_history(state.history_turns)
