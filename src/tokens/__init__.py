"""Public API for token utilities (exact semantics)."""

from .token_utils import (
    # Chat-specific
    count_tokens_chat,
    trim_text_to_token_limit_chat,
    trim_history_preserve_messages_chat,
    # Tool-specific
    count_tokens_tool,
    trim_text_to_token_limit_tool,
    trim_history_preserve_messages_tool,
    trim_history_for_tool_sharing,
    # Back-compat aliases
    count_tokens,
    trim_text_to_token_limit,
    trim_history_preserve_messages,
)

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
    # Back-compat
    "count_tokens",
    "trim_text_to_token_limit",
    "trim_history_preserve_messages",
]


