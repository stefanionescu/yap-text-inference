"""Token utilities built on top of the model-specific tokenizers.

This module provides exact token counting, trimming, and history formatting
for chat and tool models separately, ensuring KV cache accounting
matches the deployed model tokenizers.

Key Functions:

count_tokens_*(): Return exact token count using the model's tokenizer.
    Used for budget checking and logging.

trim_text_to_token_limit_*(): Trim text to fit within a token budget.
    Supports keeping "start" (prefix) or "end" (suffix) of text.

build_user_history_for_tool(): Format user-only messages (no assistant)
    for the tool model, trimmed to fit token budget.

All functions are logged at DEBUG level with input/output metrics.
"""

from __future__ import annotations

import logging
from .registry import get_chat_tokenizer, get_tool_tokenizer

logger = logging.getLogger(__name__)


_NEWLINE_TOKEN_CACHE: list[int] = []


def _get_newline_tokens() -> int:
    if not _NEWLINE_TOKEN_CACHE:
        _NEWLINE_TOKEN_CACHE.append(count_tokens_tool("\n"))
    return _NEWLINE_TOKEN_CACHE[0]


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


def build_user_history_for_tool(
    user_texts: list[str],
    max_tokens: int,
) -> str:
    """Format + trim user-only history for the tool model.

    Args:
        user_texts: Raw user utterances (most recent last).
        max_tokens: Maximum token budget for the formatted history.

    Returns:
        A newline-joined string of raw user utterances:

            hi
            show me your screen

        trimmed to <= max_tokens using the tool tokenizer for exact counts.
    """
    if max_tokens <= 0 or not user_texts:
        return ""

    newline_tokens = _get_newline_tokens()
    selected: list[str] = []
    total_tokens = 0

    for text in reversed(user_texts):
        stripped = text.strip()
        if not stripped:
            continue
        line_tokens = count_tokens_tool(stripped)
        if not selected and line_tokens > max_tokens:
            # If latest utterance alone exceeds budget, keep the most recent tail.
            clipped = trim_text_to_token_limit_tool(stripped, max_tokens=max_tokens, keep="end").strip()
            if clipped:
                selected.insert(0, clipped)
            break
        additional = line_tokens
        if selected:
            additional += newline_tokens
        if total_tokens + additional > max_tokens:
            break
        selected.insert(0, stripped)
        total_tokens += additional

    return "\n".join(selected)


__all__ = [
    # Chat
    "count_tokens_chat",
    "trim_text_to_token_limit_chat",
    # Tool
    "count_tokens_tool",
    "trim_text_to_token_limit_tool",
    "build_user_history_for_tool",
]
