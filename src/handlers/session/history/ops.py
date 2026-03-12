"""Pure operations for rendering, extracting, and trimming session history."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar
from .settings import HistoryRuntimeConfig
from src.state.session import ChatMessage, HistoryTurn, SessionState
from src.helpers.chat_history import group_chat_turns, flatten_chat_turns
from src.tokens.history import count_chat_tokens, count_tool_tokens, build_tool_history, trim_tool_text_to_budget

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer

T = TypeVar("T")


def _trim_oldest_items(
    items: list[T],
    *,
    target_tokens: int,
    count_tokens: Callable[[list[T]], int],
) -> list[T]:
    """Drop oldest items until ``count_tokens(items) <= target_tokens``."""
    tokens = count_tokens(items)
    if tokens <= target_tokens:
        return items

    tokens_to_remove = tokens - target_tokens
    avg_tokens_per_item = tokens // len(items)
    estimated_drops = max(1, tokens_to_remove // max(1, avg_tokens_per_item))
    drops = min(estimated_drops, len(items) - 1)
    trimmed = items[drops:] if drops > 0 else items

    tokens = count_tokens(trimmed)
    while len(trimmed) > 1 and tokens > target_tokens:
        trimmed.pop(0)
        tokens = count_tokens(trimmed)
    return trimmed


def render_history(messages: list[ChatMessage] | None) -> str:
    """Render stored chat history as a role-labelled transcript."""
    if not messages:
        return ""
    chunks = [f"{message.role.title()}: {message.content.strip()}" for message in messages if message.content.strip()]
    return "\n\n".join(chunks)


def get_user_texts(turns: list[HistoryTurn] | None) -> list[str]:
    """Extract raw user texts from tool-history entries."""
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
    """Trim stored chat messages when the transcript exceeds the trigger threshold."""
    messages = state.chat_history_messages
    if not messages:
        return
    turns = group_chat_turns(messages)
    if not turns:
        state.chat_history_messages = []
        return

    effective_trigger = int(trigger_tokens) if trigger_tokens is not None else config.chat_trigger_tokens
    effective_target = int(target_tokens) if target_tokens is not None else config.chat_target_tokens
    effective_trigger = max(1, effective_trigger)
    effective_target = max(1, min(effective_target, effective_trigger))

    def _count(candidate_turns: list[list[ChatMessage]]) -> int:
        return count_chat_tokens(render_history(flatten_chat_turns(candidate_turns)), chat_tokenizer)

    if _count(turns) <= effective_trigger:
        return
    trimmed_turns = _trim_oldest_items(
        turns,
        target_tokens=effective_target,
        count_tokens=_count,
    )
    state.chat_history_messages = flatten_chat_turns(trimmed_turns)


def trim_tool_history(
    state: SessionState,
    budget: int,
    *,
    tool_tokenizer: FastTokenizer | None = None,
) -> None:
    """Trim tool-history entries to fit within ``budget`` tokens."""
    turns = state.tool_history_turns
    if not turns:
        return

    effective_budget = max(1, int(budget))

    def _count(candidate_turns: list[HistoryTurn]) -> int:
        texts = get_user_texts(candidate_turns)
        return count_tool_tokens("\n".join(texts), tool_tokenizer, include_special_tokens=True)

    if _count(turns) <= effective_budget:
        return
    trimmed_turns = _trim_oldest_items(turns, target_tokens=effective_budget, count_tokens=_count)
    if trimmed_turns:
        remaining_tokens = _count(trimmed_turns)
        if remaining_tokens > effective_budget and len(trimmed_turns) == 1:
            last_turn = trimmed_turns[0]
            clipped_user = trim_tool_text_to_budget(
                last_turn.user,
                effective_budget,
                tool_tokenizer,
                keep="end",
                include_special_tokens=True,
            )
            trimmed_turns = (
                [HistoryTurn(turn_id=last_turn.turn_id, user=clipped_user, assistant="")] if clipped_user else []
            )
    state.tool_history_turns = trimmed_turns


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
    return build_tool_history(
        user_texts,
        budget,
        tool_tokenizer,
        oversize_policy="trim_latest_tail",
    )


__all__ = [
    "render_history",
    "trim_chat_history",
    "trim_tool_history",
    "render_tool_history_text",
    "get_user_texts",
]
