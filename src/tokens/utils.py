"""Token utilities built on top of the configured runtime tokenizers."""

from __future__ import annotations

import logging
from .history import (
    build_tool_history,
    count_chat_tokens as _count_chat_tokens,
    count_tool_tokens as _count_tool_tokens,
)
from .registry import get_chat_tokenizer, get_tool_tokenizer

logger = logging.getLogger(__name__)


def count_tokens_chat(text: str) -> int:
    """Return token count using the chat model tokenizer."""
    n = _count_chat_tokens(text, get_chat_tokenizer())
    # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
    logger.debug("tokens.chat.count: len_chars=%s tokens=%s", len(text), n)
    return n


def count_tokens_tool(text: str) -> int:
    """Return token count using the tool model tokenizer."""
    n = _count_tool_tokens(text, get_tool_tokenizer())
    # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
    logger.debug("tokens.tool.count: len_chars=%s tokens=%s", len(text), n)
    return n


def trim_text_to_token_limit_chat(text: str, max_tokens: int, keep: str = "end") -> str:
    """Trim text using the chat model tokenizer (exact)."""
    out = get_chat_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)
    # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
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
    # nosemgrep: python.lang.security.audit.logging.logger-credential-leak.python-logger-credential-disclosure
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
    """Format + trim user-only history for the tool model."""
    return build_tool_history(
        user_texts,
        max_tokens,
        get_tool_tokenizer(),
        oversize_policy="trim_latest_tail",
    )


__all__ = [
    # Chat
    "count_tokens_chat",
    "trim_text_to_token_limit_chat",
    # Tool
    "count_tokens_tool",
    "trim_text_to_token_limit_tool",
    "build_user_history_for_tool",
]
