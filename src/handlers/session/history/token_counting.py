"""Token counting and line-level history helpers for session history handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _fallback_count_tokens(text: str, *, include_special_tokens: bool = False) -> int:
    _ = include_special_tokens
    if not text:
        return 0
    return len(text.split())


def count_chat_tokens(text: str, chat_tokenizer: FastTokenizer | None) -> int:
    if not text:
        return 0
    if chat_tokenizer is not None:
        return chat_tokenizer.count(text)
    return _fallback_count_tokens(text)


def count_tool_tokens(
    text: str,
    tool_tokenizer: FastTokenizer | None,
    *,
    include_special_tokens: bool = False,
) -> int:
    if not text:
        return 0
    if tool_tokenizer is not None:
        return tool_tokenizer.count(text, add_special_tokens=include_special_tokens)
    return _fallback_count_tokens(text, include_special_tokens=include_special_tokens)


def build_tool_history(
    user_texts: list[str],
    budget: int,
    tool_tokenizer: FastTokenizer | None,
) -> str:
    selected_lines: list[str] = []

    for text in reversed(user_texts):
        stripped = text.strip()
        if not stripped:
            continue

        candidate_lines = [stripped] + selected_lines
        candidate_text = "\n".join(candidate_lines)
        candidate_tokens = count_tool_tokens(
            candidate_text,
            tool_tokenizer,
            include_special_tokens=True,
        )
        if candidate_tokens <= budget:
            selected_lines.insert(0, stripped)
            continue

        if not selected_lines:
            # Keep the latest line whole even if it exceeds budget; downstream
            # tokenizer truncation remains the final hard limit.
            selected_lines.insert(0, stripped)
        break

    return "\n".join(selected_lines)


__all__ = [
    "count_chat_tokens",
    "count_tool_tokens",
    "build_tool_history",
]
