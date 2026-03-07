"""Pure operations for rendering, extracting, and trimming session history."""

from __future__ import annotations

from typing import TYPE_CHECKING
from collections.abc import Callable
from .settings import HistoryRuntimeConfig
from src.state.session import HistoryTurn, SessionState
from .token_counting import count_chat_tokens, count_tool_tokens, build_tool_history

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _trim_oldest_turns(
    turns: list[HistoryTurn],
    *,
    target_tokens: int,
    count_tokens: Callable[[list[HistoryTurn]], int],
) -> list[HistoryTurn]:
    """Drop oldest turns until count_tokens(turns) <= target_tokens.

    Uses a two-step strategy:
    1. Batch-drop estimated turns using average tokens-per-turn.
    2. Verify with one-by-one drops as needed.

    The newest turn is always preserved.
    """
    tokens = count_tokens(turns)
    if tokens <= target_tokens:
        return turns

    tokens_to_remove = tokens - target_tokens
    avg_tokens_per_turn = tokens // len(turns)
    estimated_drops = max(1, tokens_to_remove // max(1, avg_tokens_per_turn))
    drops = min(estimated_drops, len(turns) - 1)
    trimmed = turns[drops:] if drops > 0 else turns

    tokens = count_tokens(trimmed)
    while len(trimmed) > 1 and tokens > target_tokens:
        trimmed.pop(0)
        tokens = count_tokens(trimmed)
    return trimmed


def render_history(turns: list[HistoryTurn] | None) -> str:
    """Render history turns to text format for prompt building."""
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


def get_user_texts(turns: list[HistoryTurn] | None) -> list[str]:
    """Extract raw user texts from history turns."""
    if not turns:
        return []
    return [s for turn in turns if turn.user and (s := turn.user.strip())]


def trim_chat_history(
    state: SessionState,
    *,
    config: HistoryRuntimeConfig,
    chat_tokenizer: FastTokenizer | None = None,
    trigger_tokens: int | None = None,
    target_tokens: int | None = None,
) -> None:
    """Trim chat history when it exceeds the configured trigger threshold."""
    turns = state.history_turns
    if not turns:
        return

    effective_trigger = int(trigger_tokens) if trigger_tokens is not None else config.chat_trigger_tokens
    effective_target = int(target_tokens) if target_tokens is not None else config.chat_target_tokens
    effective_trigger = max(1, effective_trigger)
    effective_target = max(1, min(effective_target, effective_trigger))

    def _count(candidate_turns: list[HistoryTurn]) -> int:
        return count_chat_tokens(render_history(candidate_turns), chat_tokenizer)

    if _count(turns) <= effective_trigger:
        return
    state.history_turns = _trim_oldest_turns(turns, target_tokens=effective_target, count_tokens=_count)


def trim_tool_history(
    state: SessionState,
    budget: int,
    *,
    tool_tokenizer: FastTokenizer | None = None,
) -> None:
    """Trim tool_history_turns to fit within budget tokens (no hysteresis)."""
    turns = state.tool_history_turns
    if not turns:
        return

    effective_budget = max(1, int(budget))

    def _count(candidate_turns: list[HistoryTurn]) -> int:
        texts = get_user_texts(candidate_turns)
        return count_tool_tokens("\n".join(texts), tool_tokenizer, include_special_tokens=True)

    if _count(turns) <= effective_budget:
        return
    state.tool_history_turns = _trim_oldest_turns(turns, target_tokens=effective_budget, count_tokens=_count)


def render_tool_history_text(
    turns: list[HistoryTurn] | None,
    *,
    config: HistoryRuntimeConfig,
    max_tokens: int | None = None,
    tool_tokenizer: FastTokenizer | None = None,
) -> str:
    """Render user-only history trimmed for the tool model."""
    if not config.deploy_tool:
        return ""
    user_texts = get_user_texts(turns)
    if not user_texts:
        return ""

    default_budget = config.default_tool_history_tokens or 1536
    budget = max(1, int(max_tokens if max_tokens is not None else default_budget))
    return build_tool_history(user_texts, budget, tool_tokenizer)


__all__ = [
    "render_history",
    "trim_chat_history",
    "trim_tool_history",
    "render_tool_history_text",
    "get_user_texts",
]
