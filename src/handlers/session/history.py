"""History rendering, trimming, and controller utilities.

This module handles the transformation between structured conversation history
(HistoryTurn objects) and text representations. It supports:

1. Rendering: Converting structured turns to text format for prompt building
2. Trimming: Keeping history within token budgets independently for chat and tool
3. Extraction: Getting user-only texts for tool routing

For parsing functions (text/JSON to HistoryTurn), see the parsing module.

Chat history uses a two-threshold (hysteresis) approach:
- Triggers at CHAT_HISTORY_MAX_TOKENS, trims to TRIMMED_HISTORY_LENGTH

Tool history is maintained in a separate list (state.tool_history_turns) and
trimmed directly to a caller-supplied budget with no hysteresis.

Storage is deployment-mode aware:
- chat-only: state.history_turns is active, state.tool_history_turns is inactive
- tool-only: state.tool_history_turns is active, state.history_turns is inactive
- both: both stores are active

History is cropped eagerly at import time (set_turns / set_text) using the
retention-adjusted trigger, then maintained on each access via the full budget.

The HistoryController class provides a clean interface for session-scoped
history operations, ensuring proper trimming occurs on access.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from src.config.tool import TOOL_HISTORY_TOKENS
from src.state.session import HistoryTurn, SessionState
from .parsing import parse_history_text, parse_history_as_tuples
from src.config import DEPLOY_CHAT, DEPLOY_TOOL, TRIMMED_HISTORY_LENGTH, CHAT_HISTORY_MAX_TOKENS
from .history_tokens import trim_tool_text, count_chat_tokens, count_tool_tokens, build_tool_history

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _eager_trigger() -> int:
    """Return the import-time trigger threshold for the active deploy mode."""
    return TRIMMED_HISTORY_LENGTH


def render_history(turns: list[HistoryTurn] | None) -> str:
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
    chat_tokenizer: FastTokenizer | None = None,
    trigger_tokens: int | None = None,
    target_tokens: int | None = None,
) -> None:
    """Trim chat history when it exceeds the configured trigger.

    Uses a two-threshold (hysteresis) approach:
    - Triggers at CHAT_HISTORY_MAX_TOKENS, trims to TRIMMED_HISTORY_LENGTH

    Supplying a lower trigger (e.g., the retention-adjusted target) forces
    eager trimming, which is useful when importing client-provided history.
    """
    turns = state.history_turns
    if not turns:
        return

    default_trigger = CHAT_HISTORY_MAX_TOKENS
    default_target = TRIMMED_HISTORY_LENGTH

    def _count() -> int:
        rendered = render_history(turns)
        return count_chat_tokens(rendered, chat_tokenizer)

    effective_trigger = trigger_tokens or default_trigger
    effective_target = target_tokens or default_target
    effective_target = min(effective_target, effective_trigger)

    tokens = _count()
    if tokens <= effective_trigger:
        return

    # Calculate tokens to remove and estimate turns to drop
    tokens_to_remove = tokens - effective_target
    avg_tokens_per_turn = tokens // len(turns)
    estimated_drops = max(1, tokens_to_remove // max(1, avg_tokens_per_turn))

    # Drop estimated turns in one batch (capped to leave at least 1 turn)
    drops = min(estimated_drops, len(turns) - 1)
    if drops > 0:
        turns = turns[drops:]
        state.history_turns = turns

    # Verify and adjust if still over target (never drop the very last turn)
    tokens = _count()
    while len(turns) > 1 and tokens > effective_target:
        turns.pop(0)
        tokens = _count()


def trim_tool_history(
    state: SessionState,
    budget: int,
    *,
    tool_tokenizer: FastTokenizer | None = None,
) -> None:
    """Trim tool_history_turns to fit within *budget* tokens (no hysteresis)."""
    turns = state.tool_history_turns
    if not turns:
        return

    def _count() -> int:
        texts = get_user_texts(turns)
        return count_tool_tokens("\n".join(texts), tool_tokenizer)

    tokens = _count()
    if tokens <= budget:
        return

    # Batch-drop estimated turns
    tokens_to_remove = tokens - budget
    avg = tokens // len(turns)
    drops = min(max(1, tokens_to_remove // max(1, avg)), len(turns) - 1)
    if drops > 0:
        turns = turns[drops:]
        state.tool_history_turns = turns

    # One-by-one verify
    tokens = _count()
    while len(turns) > 1 and tokens > budget:
        turns.pop(0)
        tokens = _count()

    # Clip oversized last turn in-place
    if turns and _count() > budget:
        turn = turns[-1]
        user_text = (turn.user or "").strip()
        if user_text:
            turn.user = trim_tool_text(user_text, max_tokens=budget, tool_tokenizer=tool_tokenizer)


def render_tool_history_text(
    turns: list[HistoryTurn] | None,
    *,
    max_tokens: int | None = None,
    tool_tokenizer: FastTokenizer | None = None,
) -> str:
    """Render user-only history trimmed for the tool model."""
    if not DEPLOY_TOOL:
        return ""
    user_texts = get_user_texts(turns)
    if not user_texts:
        return ""

    budget = max(1, int(max_tokens if max_tokens is not None else TOOL_HISTORY_TOKENS or 1536))
    return build_tool_history(
        user_texts,
        budget,
        tool_tokenizer,
    )


def get_user_texts(turns: list[HistoryTurn] | None) -> list[str]:
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

    Chat and tool histories are maintained independently when both are deployed.
    When only one mode is deployed, the inactive store is forced to None.
    """

    def __init__(
        self,
        *,
        tool_history_budget: int | None = None,
        chat_tokenizer: FastTokenizer | None = None,
        tool_tokenizer: FastTokenizer | None = None,
    ):
        self._tool_budget = tool_history_budget
        self._chat_tokenizer = chat_tokenizer
        self._tool_tokenizer = tool_tokenizer

    def _sync_mode_storage(self, state: SessionState) -> None:
        """Keep only active history stores populated for the current deploy mode."""
        if DEPLOY_CHAT:
            if state.history_turns is None:
                state.history_turns = []
        else:
            state.history_turns = None

        if DEPLOY_TOOL:
            if state.tool_history_turns is None:
                state.tool_history_turns = []
        else:
            state.tool_history_turns = None

    def initialize_mode_state(self, state: SessionState) -> None:
        """Initialize/normalize history stores for deployment mode."""
        self._sync_mode_storage(state)

    def _chat_turns(self, state: SessionState) -> list[HistoryTurn]:
        turns = state.history_turns
        return turns if turns is not None else []

    def _tool_turns(self, state: SessionState) -> list[HistoryTurn]:
        turns = state.tool_history_turns
        return turns if turns is not None else []

    def get_text(self, state: SessionState) -> str:
        """Get full rendered history (User + Assistant turns).

        Triggers trimming before rendering to ensure budget compliance.

        Args:
            state: The session state containing history turns.

        Returns:
            Formatted history text.
        """
        self._sync_mode_storage(state)
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer)
        return render_history(self._chat_turns(state))

    def get_turns(self, state: SessionState) -> list[HistoryTurn]:
        """Get a copy of chat history turns after applying trim policy."""
        self._sync_mode_storage(state)
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer)
        return [HistoryTurn(turn_id=t.turn_id, user=t.user, assistant=t.assistant) for t in self._chat_turns(state)]

    def get_user_texts(self, state: SessionState) -> list[str]:
        """Get raw user texts for the appropriate deploy mode."""
        self._sync_mode_storage(state)
        if DEPLOY_TOOL and self._tool_budget:
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
            return get_user_texts(self._tool_turns(state))
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer)
        return get_user_texts(self._chat_turns(state))

    def get_tool_history_text(self, state: SessionState, *, max_tokens: int | None = None) -> str:
        """Get trimmed user-only history for the tool model."""
        self._sync_mode_storage(state)
        if DEPLOY_TOOL and self._tool_budget:
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
            return render_tool_history_text(
                self._tool_turns(state),
                max_tokens=max_tokens or self._tool_budget,
                tool_tokenizer=self._tool_tokenizer,
            )
        return render_tool_history_text(
            self._chat_turns(state),
            max_tokens=max_tokens,
            tool_tokenizer=self._tool_tokenizer,
        )

    def set_text(self, state: SessionState, history_text: str) -> str:
        self._sync_mode_storage(state)
        parsed_turns = parse_history_text(history_text)
        if DEPLOY_CHAT:
            state.history_turns = parsed_turns
        else:
            state.history_turns = None
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer, trigger_tokens=_eager_trigger())
        if DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns = [
                HistoryTurn(turn_id=t.turn_id, user=t.user, assistant="")
                for t in parsed_turns
                if (t.user or "").strip()
            ]
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
        return render_history(self._chat_turns(state))

    def set_turns(self, state: SessionState, turns: list[HistoryTurn]) -> str:
        """Set history from pre-parsed turns and apply import-time trimming."""
        self._sync_mode_storage(state)
        if DEPLOY_CHAT:
            state.history_turns = turns
        else:
            state.history_turns = None
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer, trigger_tokens=_eager_trigger())
        if DEPLOY_TOOL and self._tool_budget:
            state.tool_history_turns = [
                HistoryTurn(turn_id=t.turn_id, user=t.user, assistant="") for t in turns if (t.user or "").strip()
            ]
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
        return render_history(self._chat_turns(state))

    def append_user_turn(self, state: SessionState, user_utt: str) -> str | None:
        self._sync_mode_storage(state)
        user = (user_utt or "").strip()
        if not user:
            return None
        turn_id = uuid.uuid4().hex
        if DEPLOY_CHAT:
            self._chat_turns(state).append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
            trim_history(state, chat_tokenizer=self._chat_tokenizer)
        if DEPLOY_TOOL and self._tool_budget:
            self._tool_turns(state).append(HistoryTurn(turn_id=turn_id, user=user, assistant=""))
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
        return turn_id

    def append_turn(
        self,
        state: SessionState,
        user_utt: str,
        assistant_text: str,
        *,
        turn_id: str | None = None,
    ) -> str:
        self._sync_mode_storage(state)
        user = (user_utt or "").strip()
        assistant = assistant_text or ""

        chat_turns = self._chat_turns(state)
        if turn_id and DEPLOY_CHAT:
            target = next((t for t in chat_turns if t.turn_id == turn_id), None)
            if target is not None:
                if assistant:
                    target.assistant = assistant
                if DEPLOY_CHAT:
                    trim_history(state, chat_tokenizer=self._chat_tokenizer)
                return render_history(chat_turns)

        if not user and not assistant:
            return render_history(chat_turns)

        new_turn_id = turn_id or uuid.uuid4().hex
        if DEPLOY_CHAT:
            chat_turns.append(
                HistoryTurn(
                    turn_id=new_turn_id,
                    user=user,
                    assistant=assistant,
                )
            )
        if DEPLOY_CHAT:
            trim_history(state, chat_tokenizer=self._chat_tokenizer)
        if user and DEPLOY_TOOL and self._tool_budget:
            self._tool_turns(state).append(HistoryTurn(turn_id=new_turn_id, user=user, assistant=""))
            trim_tool_history(state, self._tool_budget, tool_tokenizer=self._tool_tokenizer)
        return render_history(chat_turns)


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
