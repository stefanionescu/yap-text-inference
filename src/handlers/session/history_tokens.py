"""Token counting and trimming helpers for session history handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _fallback_count_tokens(text: str) -> int:
    return len(text.split())


def _fallback_trim_end(text: str, max_tokens: int) -> str:
    if max_tokens <= 0:
        return ""
    tokens = text.split()
    if len(tokens) <= max_tokens:
        return text
    return " ".join(tokens[-max_tokens:])


def count_chat_tokens(text: str, chat_tokenizer: FastTokenizer | None) -> int:
    if not text:
        return 0
    if chat_tokenizer is not None:
        return chat_tokenizer.count(text)
    return _fallback_count_tokens(text)


def count_tool_tokens(text: str, tool_tokenizer: FastTokenizer | None) -> int:
    if not text:
        return 0
    if tool_tokenizer is not None:
        return tool_tokenizer.count(text)
    return _fallback_count_tokens(text)


def trim_tool_text(text: str, max_tokens: int, tool_tokenizer: FastTokenizer | None) -> str:
    if tool_tokenizer is not None:
        return tool_tokenizer.trim(text, max_tokens=max_tokens, keep="end")
    return _fallback_trim_end(text, max_tokens)


def build_tool_history(
    user_texts: list[str],
    budget: int,
    tool_tokenizer: FastTokenizer | None,
) -> str:
    if tool_tokenizer is None:
        selected: list[str] = []
        total_tokens = 0
        for text in reversed(user_texts):
            stripped = text.strip()
            if not stripped:
                continue
            line_tokens = _fallback_count_tokens(stripped)
            if not selected and line_tokens > budget:
                clipped = _fallback_trim_end(stripped, budget).strip()
                if clipped:
                    selected.insert(0, clipped)
                break
            additional = line_tokens + (1 if selected else 0)
            if total_tokens + additional > budget:
                break
            selected.insert(0, stripped)
            total_tokens += additional
        return "\n".join(selected)

    newline_tokens = tool_tokenizer.count("\n")
    selected_lines: list[str] = []
    total_tokens = 0

    for text in reversed(user_texts):
        stripped = text.strip()
        if not stripped:
            continue
        line_tokens = tool_tokenizer.count(stripped)
        if not selected_lines and line_tokens > budget:
            clipped = tool_tokenizer.trim(stripped, max_tokens=budget, keep="end").strip()
            if clipped:
                selected_lines.insert(0, clipped)
            break
        additional = line_tokens + (newline_tokens if selected_lines else 0)
        if total_tokens + additional > budget:
            break
        selected_lines.insert(0, stripped)
        total_tokens += additional

    return "\n".join(selected_lines)


__all__ = [
    "count_chat_tokens",
    "count_tool_tokens",
    "trim_tool_text",
    "build_tool_history",
]
