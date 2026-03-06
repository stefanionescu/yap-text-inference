"""History rendering, trimming, and controller utilities.

This module handles the transformation between structured conversation history
(HistoryTurn objects) and text representations. It supports:

1. Rendering: Converting structured turns to text format for prompt building
2. Trimming: Keeping history within token budgets independently for chat and tool
3. Extraction: Getting user-only texts for tool routing

For parsing functions (text/JSON to HistoryTurn), see the parsing module.

Chat history uses a two-threshold (hysteresis) approach:
- Triggers at HISTORY_MAX_TOKENS, trims to TRIMMED_HISTORY_LENGTH

Tool history is maintained in a separate list (state.tool_history_turns) and
trimmed directly to a caller-supplied budget with no hysteresis.

History is cropped eagerly at import time (set_turns / set_text) using the
retention-adjusted trigger, then maintained on each access via the full budget.

The HistoryController class provides a clean interface for session-scoped
history operations, ensuring proper trimming occurs on access.
"""

from __future__ import annotations

import uuid
from src.state.session import HistoryTurn, SessionState
from .parsing import parse_history_text, parse_history_as_tuples
from src.tokens import count_tokens_chat, count_tokens_tool, build_user_history_for_tool, trim_text_to_token_limit_tool
from src.config import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    HISTORY_MAX_TOKENS,
    TRIMMED_HISTORY_LENGTH,
)


def _eager_trigger() -> int:
    """Return the import-time trigger threshold for the active deploy mode."""
    return TRIMMED_HISTORY_LENGTH


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
) -> None:
    """Trim chat history when it exceeds the configured trigger.

    Uses a two-threshold (hysteresis) approach:
    - Triggers at HISTORY_MAX_TOKENS, trims to TRIMMED_HISTORY_LENGTH

    Supplying a lower trigger (e.g., the retention-adjusted target) forces
    eager trimming, which is useful when importing client-provided history.
    """
    if not state.history_turns:
        return

    default_trigger = HISTORY_MAX_TOKENS
    default_target = TRIMMED_HISTORY_LENGTH

    def _count() -> int:
        rendered = render_history(state.history_turns)
        return count_tokens_chat(rendered) if rendered else 0

    effective_trigger = trigger_tokens or default_trigger
    effective_target = target_tokens or default_target
    effective_target = min(effective_target, effective_trigger)

    tokens = _count()
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

    # Verify and adjust if still over target (never drop the very last turn)
    tokens = _count()
    while len(state.history_turns) > 1 and tokens > effective_target:
        state.history_turns.pop(0)
        tokens = _count()


def trim_tool_history(state: SessionState, budget: int) -> None:
    """Trim tool_history_turns to fit within *budget* tokens (no hysteresis)."""
    if not state.tool_history_turns:
        return

    def _count() -> int:
        texts = get_user_texts(state.tool_history_turns)
        return count_tokens_tool("\n".join(texts)) if texts else 0

    tokens = _count()
    if tokens <= budget:
        return

    # Batch-drop estimated turns
    tokens_to_remove = tokens - budget
    avg = tokens // len(state.tool_history_turns)
    drops = min(max(1, tokens_to_remove // max(1, avg)), len(state.tool_history_turns) - 1)
    if drops > 0:
        state.tool_history_turns = state.tool_history_turns[drops:]

    # One-by-one verify
    tokens = _count()
    while len(state.tool_history_turns) > 1 and tokens > budget:
        state.tool_history_turns.pop(0)
        tokens = _count()

    # Clip oversized last turn in-place
    if state.tool_history_turns and _count() > budget:
        turn = state.tool_history_turns[-1]
        user_text = (turn.user or "").strip()
        if user_text:
            turn.user = trim_text_to_token_limit_tool(user_text, max_tokens=budget, keep="end")


def render_tool_history_text(turns: list[HistoryTurn], *, max_tokens: int | None = None) -> str:
    """Render user-only history trimmed for the tool model."""
    if not DEPLOY_TOOL:
        return ""
    user_texts = get_user_texts(turns)
    if not user_texts:
        return ""
    from src.config import TOOL_HISTORY_TOKENS
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
    return [s for turn in turns if turn.user and (s := turn.user.strip())]


class HistoryController:
    """History operations for SessionState.

    Provides a clean interface for managing conversation history with
    automatic trimming. All read operations trigger trimming to ensure
    the history fits within token budgets.

    Chat and tool histories are maintained independently:
    - state.history_turns: full User+Assistant turns for chat rendering
    - state.tool_history_turns: user-only turns for the tool model
    """

    def __init__(self, *, tool_history_budget: int | None = None):
        self._tool_budget = tool_history_budget

    def get_text(self, state: SessionState) -> str:
        """Get full rendered history (User + Assistant turns).

        Triggers trimming before rendering to ensure budget compliance.

        Args:
            state: The session state containing history turns.

        Returns:
            Formatted history text.
        """
        if DEPLOY_CHAT:
            trim_history(state)
        return render_history(state.history_turns)

    def get_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts for the appropriate deploy mode."""
        if DEPLOY_TOOL and self._tool_budget:
            trim_tool_history(state, self._tool_budget)
            return get_user_texts(state.tool_history_turns)
        if DEPLOY_CHAT:
            trim_history(state)
        return get_user_texts(state.history_turns)

    def get_tool_history_text(self, state: SessionState, *, max_tokens: int | None = None) -> str:
        """Get trimmed user-only history for the tool model."""
        if DEPLOY_TOOL and self._tool_budget:
            trim_tool_history(state, self._tool_budget)
            return render_tool_history_text(
                state.tool_history_turns,
                max_tokens=max_tokens or self._tool_budget,
            )
        return render_tool_history_text(state.history_turns, max_tokens=max_tokens)

    def set_text(self, state: SessionState, history_text: str) -> str:
        state.history_turns = parse_history_text(history_text)
        if DEPLOY_CHAT:
            trim_history(state, trigger_tokens=_eager_trigger())
        if DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns = [
                HistoryTurn(turn_id=t.turn_id, user=t.user, assistant="")
                for t in state.history_turns if (t.user or "").strip()
            ]
            trim_tool_history(state, self._tool_budget)
        return render_history(state.history_turns)

    def set_turns(self, state: SessionState, turns: list[HistoryTurn]) -> str:
        """Set history from pre-parsed turns and apply import-time trimming."""
        state.history_turns = turns
        if DEPLOY_CHAT:
            trim_history(state, trigger_tokens=_eager_trigger())
        if DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns = [
                HistoryTurn(turn_id=t.turn_id, user=t.user, assistant="")
                for t in turns if (t.user or "").strip()
            ]
            trim_tool_history(state, self._tool_budget)
        return render_history(state.history_turns)

    def append_user_turn(self, state: SessionState, user_utt: str) -> str | None:
        user = (user_utt or "").strip()
        if not user:
            return None
        turn_id = uuid.uuid4().hex
        state.history_turns.append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
        if DEPLOY_CHAT:
            trim_history(state)
        if DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns.append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
            trim_tool_history(state, self._tool_budget)
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
                if DEPLOY_CHAT:
                    trim_history(state)
                return render_history(state.history_turns)

        if not user and not assistant:
            return render_history(state.history_turns)

        new_turn_id = turn_id or uuid.uuid4().hex
        state.history_turns.append(
            HistoryTurn(
                turn_id=new_turn_id,
                user=user,
                assistant=assistant,
            )
        )
        if DEPLOY_CHAT:
            trim_history(state)
        if user and DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns.append(HistoryTurn(turn_id=new_turn_id, user=user, assistant=""))
            trim_tool_history(state, self._tool_budget)
        return render_history(state.history_turns)


__all__ = [
    "render_history",
    "trim_history",
    "trim_tool_history",
    "render_tool_history_text",
    "get_user_texts",
    "HistoryController",
    "parse_history_text",
    "parse_history_as_tuples",
]
