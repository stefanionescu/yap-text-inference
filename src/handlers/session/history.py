"""History rendering, trimming, and controller utilities.

This module handles the transformation between structured conversation history
(HistoryTurn objects) and text representations. It supports:

1. Rendering: Converting structured turns to text format for prompt building
2. Trimming: Keeping history within token budgets for both chat and tool models
3. Extraction: Getting user-only texts for tool routing

For parsing functions (text/JSON to HistoryTurn), see the parsing module.

Two separate trimming strategies are used:
- Chat model: Triggers at HISTORY_MAX_TOKENS, trims to TRIMMED_HISTORY_LENGTH
- Tool model: Uses TOOL_HISTORY_TOKENS and only considers user messages

The HistoryController class provides a clean interface for session-scoped
history operations, ensuring proper trimming occurs on access.
"""

from __future__ import annotations

import uuid

from src.state.session import HistoryTurn, SessionState
from src.config import DEPLOY_CHAT, DEPLOY_TOOL, HISTORY_MAX_TOKENS, TOOL_HISTORY_TOKENS, TRIMMED_HISTORY_LENGTH
from src.tokens import count_tokens_chat, count_tokens_tool, build_user_history_for_tool, trim_text_to_token_limit_tool

from .parsing import parse_history_text, parse_history_messages, parse_history_as_tuples


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


def trim_history(
    state: SessionState,
    *,
    trigger_tokens: int | None = None,
    target_tokens: int | None = None,
    tool_history_tokens: int | None = None,
) -> None:
    """Trim history when it exceeds the configured trigger.

    Uses a two-threshold (hysteresis) approach by default:
    - Triggers when tokens exceed HISTORY_MAX_TOKENS
    - Trims down to TRIMMED_HISTORY_LENGTH

    Supplying a lower trigger (e.g., TRIMMED_HISTORY_LENGTH) forces eager
    trimming, which is useful when importing client-provided history.

    When tool-only, no trimming is done here - the tool adapter
    handles its own trimming using its own tokenizer.
    """
    if not state.history_turns:
        return

    if not DEPLOY_CHAT:
        if DEPLOY_TOOL:
            _trim_history_tool(state, max_tokens=tool_history_tokens)
        return

    effective_trigger = trigger_tokens or HISTORY_MAX_TOKENS
    effective_target = target_tokens or TRIMMED_HISTORY_LENGTH
    effective_target = min(effective_target, effective_trigger)

    rendered = render_history(state.history_turns)
    if not rendered:
        state.history_turns = []
        return

    tokens = count_tokens_chat(rendered)
    # Only start trimming if we exceed the trigger threshold
    if tokens <= effective_trigger:
        return

    # Calculate tokens to remove and estimate turns to drop
    tokens_to_remove = tokens - effective_target
    avg_tokens_per_turn = tokens // len(state.history_turns)
    estimated_drops = max(1, tokens_to_remove // max(1, avg_tokens_per_turn))

    # Drop estimated turns in one batch (capped to leave at least 1 turn)
    drops = min(estimated_drops, len(state.history_turns) - 1)
    if drops > 0:
        state.history_turns = state.history_turns[drops:]

    # Verify and adjust if still over target (usually 0-1 more iterations)
    rendered = render_history(state.history_turns)
    tokens = count_tokens_chat(rendered) if rendered else 0
    while state.history_turns and tokens > effective_target:
        state.history_turns.pop(0)
        rendered = render_history(state.history_turns)
        tokens = count_tokens_chat(rendered) if rendered else 0


def _trim_history_tool(state: SessionState, *, max_tokens: int | None = None) -> None:
    """Trim history turns so user-only tokens stay within TOOL_HISTORY_TOKENS.

    In tool-only deployments, the chat trimming path is skipped.
    This keeps the in-memory turn list bounded to what the tool model
    can actually consume.
    """
    if not state.history_turns:
        return
    budget = max(1, int(max_tokens if max_tokens is not None else TOOL_HISTORY_TOKENS))
    user_texts = get_user_texts(state.history_turns)
    if not user_texts:
        state.history_turns = []
        return
    tokens = _count_user_tokens_tool(user_texts)
    if tokens <= budget:
        return
    # Drop oldest turns until user-only tokens fit
    while len(state.history_turns) > 1:
        state.history_turns.pop(0)
        user_texts = get_user_texts(state.history_turns)
        tokens = _count_user_tokens_tool(user_texts)
        if tokens <= budget:
            break

    if not state.history_turns:
        return

    latest_turn = state.history_turns[-1]
    latest_user = (latest_turn.user or "").strip()
    if latest_user and count_tokens_tool(latest_user) > budget:
        # Keep the newest tail so single-message overflows remain usable.
        latest_turn.user = trim_text_to_token_limit_tool(latest_user, max_tokens=budget, keep="end")


def _count_user_tokens_tool(user_texts: list[str]) -> int:
    """Count tool-model tokens for a list of user texts (newline-joined)."""
    if not user_texts:
        return 0
    return count_tokens_tool("\n".join(user_texts))


def render_tool_history_text(turns: list[HistoryTurn], *, max_tokens: int | None = None) -> str:
    """Render user-only history trimmed for the tool model."""
    if not DEPLOY_TOOL:
        return ""
    user_texts = get_user_texts(turns)
    if not user_texts:
        return ""
    budget = max(1, int(max_tokens if max_tokens is not None else TOOL_HISTORY_TOKENS))
    return build_user_history_for_tool(
        user_texts,
        budget,
    )


def get_user_texts(turns: list[HistoryTurn]) -> list[str]:
    """Extract raw user texts from history turns.

    Returns list of user utterances (most recent last).
    Trimming is handled by the tool adapter using its own tokenizer.
    """
    if not turns:
        return []
    return [turn.user.strip() for turn in turns if turn.user and turn.user.strip()]


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

    def get_tool_history_text(self, state: SessionState, *, max_tokens: int | None = None) -> str:
        """Get trimmed user-only history for the tool model."""
        trim_history(state, tool_history_tokens=max_tokens)
        return render_tool_history_text(state.history_turns, max_tokens=max_tokens)

    def set_text(self, state: SessionState, history_text: str) -> str:
        state.history_turns = parse_history_text(history_text)
        trim_history(state, trigger_tokens=TRIMMED_HISTORY_LENGTH)
        return render_history(state.history_turns)

    def set_messages(self, state: SessionState, messages: list[dict]) -> str:
        """Set history from JSON message array [{role, content}, ...].

        Parses messages, trims to fit token budget, returns rendered history.
        """
        state.history_turns = parse_history_messages(messages)
        trim_history(state, trigger_tokens=TRIMMED_HISTORY_LENGTH)
        return render_history(state.history_turns)

    def set_turns(self, state: SessionState, turns: list[HistoryTurn]) -> str:
        """Set history from pre-parsed turns and apply import-time trimming."""
        state.history_turns = turns
        trim_history(state, trigger_tokens=TRIMMED_HISTORY_LENGTH)
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
            if target is not None:
                if assistant:
                    target.assistant = assistant
                trim_history(state)
                return render_history(state.history_turns)

        if not user and not assistant:
            return render_history(state.history_turns)

        state.history_turns.append(
            HistoryTurn(
                turn_id=turn_id or uuid.uuid4().hex,
                user=user,
                assistant=assistant,
            )
        )
        trim_history(state)
        return render_history(state.history_turns)


__all__ = [
    "render_history",
    "trim_history",
    "render_tool_history_text",
    "get_user_texts",
    "HistoryController",
    "parse_history_text",
    "parse_history_messages",
    "parse_history_as_tuples",
]
