"""Token counting and trimming helpers for session history handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.tokens.tokenizer import FastTokenizer


def _fallback_count_tokens(text: str, *, include_special_tokens: bool = False) -> int:
    _ = include_special_tokens
    if not text:
        return 0
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


def trim_tool_text(text: str, max_tokens: int, tool_tokenizer: FastTokenizer | None) -> str:
    if tool_tokenizer is not None:
        return tool_tokenizer.trim(text, max_tokens=max_tokens, keep="end")
    return _fallback_trim_end(text, max_tokens)


def trim_tool_text_with_special_tokens(text: str, max_tokens: int, tool_tokenizer: FastTokenizer | None) -> str:
    if max_tokens <= 0 or not text:
        return ""

    if tool_tokenizer is None:
        return _fallback_trim_end(text, max_tokens)

    if count_tool_tokens(text, tool_tokenizer, include_special_tokens=True) <= max_tokens:
        return text

    lo, hi = 0, len(tool_tokenizer.encode_ids(text))
    best = ""
    while lo <= hi:
        mid = (lo + hi) // 2
        candidate = tool_tokenizer.trim(text, max_tokens=mid, keep="end").strip()
        if not candidate:
            lo = mid + 1
            continue
        candidate_tokens = count_tool_tokens(candidate, tool_tokenizer, include_special_tokens=True)
        if candidate_tokens <= max_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1
    return best


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
            clipped = trim_tool_text_with_special_tokens(
                stripped,
                max_tokens=budget,
                tool_tokenizer=tool_tokenizer,
            ).strip()
            if clipped:
                selected_lines.insert(0, clipped)
        break

    return "\n".join(selected_lines)


__all__ = [
    "count_chat_tokens",
    "count_tool_tokens",
    "trim_tool_text",
    "trim_tool_text_with_special_tokens",
    "build_tool_history",
]
