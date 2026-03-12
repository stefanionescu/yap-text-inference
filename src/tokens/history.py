"""Pure token/history helpers shared across runtime and public wrappers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from .tokenizer import FastTokenizer


ToolHistoryOversizePolicy = Literal["keep_latest_whole", "trim_latest_tail"]


def _fallback_count_tokens(text: str, *, include_special_tokens: bool = False) -> int:
    count = len(text.split()) if text else 0
    if count and include_special_tokens:
        count += 2
    return count


def _trim_tail_to_budget(
    text: str,
    budget: int,
    tokenizer: FastTokenizer | None,
) -> str:
    if budget <= 0 or not text:
        return ""
    if tokenizer is not None:
        return tokenizer.trim(text, max_tokens=budget, keep="end").strip()
    tokens = text.split()
    if len(tokens) <= budget:
        return text
    return " ".join(tokens[-budget:])


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
    *,
    oversize_policy: ToolHistoryOversizePolicy = "keep_latest_whole",
) -> str:
    selected_lines: list[str] = []
    effective_budget = max(1, int(budget))

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
        if candidate_tokens <= effective_budget:
            selected_lines.insert(0, stripped)
            continue

        if not selected_lines:
            if oversize_policy == "trim_latest_tail":
                clipped = _trim_tail_to_budget(stripped, effective_budget, tool_tokenizer)
                if clipped:
                    selected_lines.insert(0, clipped)
            else:
                selected_lines.insert(0, stripped)
        break

    return "\n".join(selected_lines)


__all__ = [
    "ToolHistoryOversizePolicy",
    "count_chat_tokens",
    "count_tool_tokens",
    "build_tool_history",
]
