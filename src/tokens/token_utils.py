"""Token utilities built on top of the model-specific tokenizers.

Provides exact token counting, trimming, and history-aware trimming for
chat and tool models separately, ensuring KV cache accounting matches
the deployed model tokenizers.
"""

from __future__ import annotations

import logging
from .tokenizer import get_chat_tokenizer, get_tool_tokenizer

logger = logging.getLogger(__name__)


def count_tokens_chat(text: str) -> int:
    """Return token count using the chat model tokenizer."""
    n = get_chat_tokenizer().count(text)
    logger.debug("tokens.chat.count: len_chars=%s tokens=%s", len(text), n)
    return n


def count_tokens_tool(text: str) -> int:
    """Return token count using the tool model tokenizer."""
    n = get_tool_tokenizer().count(text)
    logger.debug("tokens.tool.count: len_chars=%s tokens=%s", len(text), n)
    return n


def trim_text_to_token_limit_chat(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text using the chat model tokenizer (exact)."""
    out = get_chat_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)
    logger.debug(
        "tokens.chat.trim_text: out_len=%s max_tokens=%s keep=%s",
        len(out),
        max_tokens,
        keep,
    )
    return out


def trim_text_to_token_limit_tool(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text using the tool model tokenizer (exact)."""
    out = get_tool_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)
    logger.debug(
        "tokens.tool.trim_text: out_len=%s max_tokens=%s keep=%s",
        len(out),
        max_tokens,
        keep,
    )
    return out


def _trim_history_preserve_messages_with(
    history_text: str,
    max_tokens: int,
    count_fn,
    trim_fn,
) -> str:
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
        return trim_fn(history_text, max_tokens, keep="end")

    parts = history_text.split(chosen_pattern)
    if len(parts) <= 1:
        return trim_fn(history_text, max_tokens, keep="end")

    result_parts = []
    current_tokens = 0

    for i in range(len(parts) - 1, -1, -1):
        part = parts[i]
        test_part = part if i == len(parts) - 1 else chosen_pattern + part
        part_tokens = count_fn(test_part)
        if current_tokens + part_tokens > max_tokens:
            break
        result_parts.insert(0, part)
        current_tokens += part_tokens

    if not result_parts:
        return ""

    result = result_parts[0]
    for part in result_parts[1:]:
        result += chosen_pattern + part

    out = result.strip()
    return out


def trim_history_preserve_messages_chat(history_text: str, max_tokens: int) -> str:
    out = _trim_history_preserve_messages_with(
        history_text,
        max_tokens,
        count_fn=count_tokens_chat,
        trim_fn=trim_text_to_token_limit_chat,
    )
    logger.debug(
        "tokens.chat.trim_history_preserve: in_len=%s out_len=%s max_tokens=%s",
        len(history_text),
        len(out),
        max_tokens,
    )
    return out


def trim_history_preserve_messages_tool(history_text: str, max_tokens: int) -> str:
    out = _trim_history_preserve_messages_with(
        history_text,
        max_tokens,
        count_fn=count_tokens_tool,
        trim_fn=trim_text_to_token_limit_tool,
    )
    logger.debug(
        "tokens.tool.trim_history_preserve: in_len=%s out_len=%s max_tokens=%s",
        len(history_text),
        len(out),
        max_tokens,
    )
    return out


def build_user_history_for_tool(
    user_texts: list[str],
    max_tokens: int,
    *,
    prefix: str = "USER",
) -> str:
    """Format + trim user-only history for the classifier/tool model.

    Args:
        user_texts: Raw user utterances (most recent last).
        max_tokens: Maximum token budget for the formatted history.
        prefix: Line prefix to use (default: "USER").

    Returns:
        A newline-joined string such as:

            USER: hi
            USER: show me your screen

        trimmed to <= max_tokens using the tool tokenizer for exact counts.
    """
    normalized_prefix = (prefix or "USER").strip()
    if not normalized_prefix:
        normalized_prefix = "USER"

    if max_tokens <= 0 or not user_texts:
        return ""

    newline_tokens = count_tokens_tool("\n")
    selected: list[str] = []
    total_tokens = 0

    for text in reversed(user_texts):
        stripped = text.strip()
        if not stripped:
            continue
        line = f"{normalized_prefix}: {stripped}"
        line_tokens = count_tokens_tool(line)
        additional = line_tokens
        if selected:
            additional += newline_tokens
        if selected and total_tokens + additional > max_tokens:
            break
        selected.insert(0, line)
        total_tokens += additional

    return "\n".join(selected)


__all__ = [
    # Chat
    "count_tokens_chat",
    "trim_text_to_token_limit_chat",
    "trim_history_preserve_messages_chat",
    # Tool
    "count_tokens_tool",
    "trim_text_to_token_limit_tool",
    "trim_history_preserve_messages_tool",
    "build_user_history_for_tool",
]


