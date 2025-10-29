"""Token utilities built on top of the shared tokenizer.

Provides exact token counting, trimming, and history-aware trimming.
"""

from __future__ import annotations

from .tokenizer import get_tokenizer


def count_tokens(text: str) -> int:
    """Return the exact token count for the given text."""
    return get_tokenizer().count(text)


def trim_text_to_token_limit(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text to a token limit using the shared tokenizer (exact)."""
    return get_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)


def trim_history_for_tool_sharing(history_text: str, tool_history_tokens: int) -> str:
    """Trim history for tool model KV cache sharing using exact tokenization."""
    if not history_text.strip():
        return ""
    return trim_history_preserve_messages(history_text, tool_history_tokens)


def trim_history_preserve_messages(history_text: str, max_tokens: int) -> str:
    """Trim history while preserving complete message boundaries (exact)."""
    if not history_text.strip():
        return ""

    boundary_patterns = [
        '\nUser: ',
        '\nAssistant: ',
        '\n\nUser: ',
        '\n\nAssistant: ',
        '\n\n',
        '\n',
    ]

    chosen_pattern = None
    for pattern in boundary_patterns:
        if pattern in history_text:
            chosen_pattern = pattern
            break

    if not chosen_pattern:
        return trim_text_to_token_limit(history_text, max_tokens, keep="end")

    parts = history_text.split(chosen_pattern)
    if len(parts) <= 1:
        return trim_text_to_token_limit(history_text, max_tokens, keep="end")

    result_parts = []
    current_tokens = 0

    for i in range(len(parts) - 1, -1, -1):
        part = parts[i]
        test_part = part if i == len(parts) - 1 else chosen_pattern + part
        part_tokens = count_tokens(test_part)
        if current_tokens + part_tokens > max_tokens:
            break
        result_parts.insert(0, part)
        current_tokens += part_tokens

    if not result_parts:
        return ""

    result = result_parts[0]
    for part in result_parts[1:]:
        result += chosen_pattern + part

    return result.strip()


