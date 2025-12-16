"""History parsing/rendering utilities for session handling.

This module handles the transformation between structured conversation history
(HistoryTurn objects) and text representations. It supports:

1. Rendering: Converting structured turns to text format for prompt building
2. Parsing: Converting text transcripts back to structured turns
3. Trimming: Keeping history within token budgets for both chat and tool models
4. Extraction: Getting user-only texts for classifier/tool routing

History Format:
    User: First user message
    Assistant: First assistant response
    
    User: Second user message
    Assistant: Second assistant response

Two separate trimming strategies are used:
- Chat model: Uses HISTORY_MAX_TOKENS with the chat tokenizer
- Tool model: Uses TOOL_HISTORY_TOKENS and only considers user messages

The HistoryController class provides a clean interface for session-scoped
history operations, ensuring proper trimming occurs on access.
"""

from __future__ import annotations

import uuid

from src.config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    HISTORY_MAX_TOKENS,
    TOOL_HISTORY_TOKENS,
)
from src.tokens import build_user_history_for_tool, count_tokens_chat

from .state import HistoryTurn, SessionState


def render_history(turns: list[HistoryTurn]) -> str:
    """Render history turns to text format for prompt building.
    
    Converts structured HistoryTurn objects into the standard text format:
        User: <message>
        Assistant: <response>
    
    Each turn is separated by a blank line.
    
    Args:
        turns: List of HistoryTurn objects to render.
        
    Returns:
        Formatted history text, or empty string if no turns.
    """
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
    """Parse text transcript back into structured HistoryTurn objects.
    
    Handles multi-line messages by accumulating lines until the next
    role marker (User: or Assistant:) is encountered.
    
    Args:
        history_text: Raw history in "User: X\\nAssistant: Y" format.
        
    Returns:
        List of HistoryTurn objects with generated UUIDs.
    """
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
        TOOL_HISTORY_TOKENS,
    )


def get_user_texts(turns: list[HistoryTurn]) -> list[str]:
    """Extract raw user texts from history turns.
    
    Returns list of user utterances (most recent last).
    Trimming is handled by the classifier adapter using its own tokenizer.
    """
    if not turns:
        return []
    return [turn.user.strip() for turn in turns if turn.user and turn.user.strip()]


def parse_history_as_tuples(history_text: str) -> list[tuple[str, str]]:
    """Parse history text into (user, assistant) tuples.
    
    This is a convenience wrapper around parse_history_text for callers
    that need the simpler tuple format (e.g., prompt builders).
    
    Args:
        history_text: Raw history in "User: X\nAssistant: Y" format
        
    Returns:
        List of (user_text, assistant_text) tuples
    """
    turns = parse_history_text(history_text)
    return [(turn.user, turn.assistant) for turn in turns]


class HistoryController:
    """History operations for SessionState.
    
    Provides a clean interface for managing conversation history with
    automatic trimming. All read operations trigger trimming to ensure
    the history fits within token budgets.
    
    This class is stateless - all state is stored in SessionState objects.
    A single HistoryController instance is typically shared across sessions.
    """

    def get_text(self, state: SessionState) -> str:
        """Get full rendered history (User + Assistant turns).
        
        Triggers trimming before rendering to ensure budget compliance.
        
        Args:
            state: The session state containing history turns.
            
        Returns:
            Formatted history text.
        """
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
