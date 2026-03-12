"""Exact tool-input budgeting helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from src.tokens.history import count_tool_tokens

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


@dataclass(frozen=True, slots=True)
class ToolFitResult:
    """Exact tool-input fit result used before backend calls."""

    tool_user_history: str
    tool_user_utt: str
    input_tokens: int


def _normalize_user_texts(user_texts: list[str]) -> list[str]:
    return [text.strip() for text in user_texts if (text or "").strip()]


def _join_tool_input(history_lines: list[str], tool_user_utt: str) -> str:
    parts = []
    history_text = "\n".join(history_lines).strip()
    if history_text:
        parts.append(history_text)
    user_text = (tool_user_utt or "").strip()
    if user_text:
        parts.append(user_text)
    return "\n".join(parts)


def _count_input_tokens(
    history_lines: list[str],
    tool_user_utt: str,
    tool_tokenizer: FastTokenizer | None,
) -> int:
    return count_tool_tokens(
        _join_tool_input(history_lines, tool_user_utt),
        tool_tokenizer,
        include_special_tokens=True,
    )


def _count_user_tokens(tool_user_utt: str, tool_tokenizer: FastTokenizer | None) -> int:
    return count_tool_tokens(tool_user_utt, tool_tokenizer, include_special_tokens=False)


def _trim_tool_user(tool_user_utt: str, remaining_tokens: int, tool_tokenizer: FastTokenizer | None) -> str:
    user = (tool_user_utt or "").strip()
    if remaining_tokens <= 0 or not user:
        return ""
    if tool_tokenizer is not None:
        return tool_tokenizer.trim(user, max_tokens=remaining_tokens, keep="end").strip()
    tokens = user.split()
    if len(tokens) <= remaining_tokens:
        return user
    return " ".join(tokens[-remaining_tokens:])


def _fit_current_user_to_budget(
    raw_tool_user_utt: str,
    history_lines: list[str],
    tool_tokenizer: FastTokenizer | None,
    *,
    max_input_tokens: int,
) -> tuple[str, int]:
    candidate = (raw_tool_user_utt or "").strip()
    if not candidate:
        return "", _count_input_tokens(history_lines, "", tool_tokenizer)

    token_count = _count_user_tokens(candidate, tool_tokenizer)
    for remaining in range(token_count, 0, -1):
        trimmed = _trim_tool_user(candidate, remaining, tool_tokenizer)
        input_tokens = _count_input_tokens(history_lines, trimmed, tool_tokenizer)
        if input_tokens <= max_input_tokens:
            return trimmed, input_tokens

    raise ValueError("tool input exceeds exact budget even after removing all history and trimming the user turn")


def fit_tool_input_to_budget(
    prior_user_texts: list[str],
    tool_user_utt: str,
    tool_tokenizer: FastTokenizer | None,
    *,
    max_input_tokens: int,
) -> ToolFitResult:
    """Fit the exact combined tool input to ``max_input_tokens`` before backend call."""
    if max_input_tokens <= 0:
        raise ValueError("tool input exceeds exact budget before backend call")
    effective_history = _normalize_user_texts(prior_user_texts)
    raw_user = (tool_user_utt or "").strip()
    input_tokens = _count_input_tokens(effective_history, raw_user, tool_tokenizer)

    while effective_history and input_tokens > max_input_tokens:
        effective_history = effective_history[1:]
        input_tokens = _count_input_tokens(effective_history, raw_user, tool_tokenizer)

    effective_user = raw_user
    if input_tokens > max_input_tokens:
        effective_user, input_tokens = _fit_current_user_to_budget(
            raw_user,
            effective_history,
            tool_tokenizer,
            max_input_tokens=max_input_tokens,
        )

    if input_tokens > max_input_tokens:
        raise ValueError("tool input exceeds exact budget before backend call")

    return ToolFitResult(
        tool_user_history="\n".join(effective_history),
        tool_user_utt=effective_user,
        input_tokens=input_tokens,
    )


__all__ = ["ToolFitResult", "fit_tool_input_to_budget"]
