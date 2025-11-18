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
    logger.info(f"tokens.chat.count: len_chars={len(text)} tokens={n}")
    return n


def count_tokens_tool(text: str) -> int:
    """Return token count using the tool model tokenizer."""
    n = get_tool_tokenizer().count(text)
    logger.info(f"tokens.tool.count: len_chars={len(text)} tokens={n}")
    return n


def trim_text_to_token_limit_chat(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text using the chat model tokenizer (exact)."""
    out = get_chat_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)
    logger.info(f"tokens.chat.trim_text: out_len={len(out)} max_tokens={max_tokens} keep={keep}")
    return out


def trim_text_to_token_limit_tool(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text using the tool model tokenizer (exact)."""
    out = get_tool_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)
    logger.info(f"tokens.tool.trim_text: out_len={len(out)} max_tokens={max_tokens} keep={keep}")
    return out


def trim_history_for_tool_sharing(history_text: str, tool_history_tokens: int) -> str:
    """Trim history for tool model KV cache sharing using tool tokenizer."""
    if not history_text.strip():
        return ""
    out = trim_history_preserve_messages_tool(history_text, tool_history_tokens)
    logger.info(
        "tokens.tool.trim_history_for_tool: in_len=%s out_len=%s max_tokens=%s",
        len(history_text),
        len(out),
        tool_history_tokens,
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
    logger.info(
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
    logger.info(
        "tokens.tool.trim_history_preserve: in_len=%s out_len=%s max_tokens=%s",
        len(history_text),
        len(out),
        max_tokens,
    )
    return out


__all__ = [
    # Chat
    "count_tokens_chat",
    "trim_text_to_token_limit_chat",
    "trim_history_preserve_messages_chat",
    # Tool
    "count_tokens_tool",
    "trim_text_to_token_limit_tool",
    "trim_history_preserve_messages_tool",
    "trim_history_for_tool_sharing",
]


