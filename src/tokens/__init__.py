"""Public API for token utilities (exact semantics).

This package provides token counting and trimming functions that use
the actual deployed model tokenizers for exact results. This ensures:

1. Token counts match what the model sees
2. KV cache budget accounting is accurate
3. History trimming preserves complete message boundaries

Two sets of functions are provided:

Chat Model Functions (use CHAT_MODEL tokenizer):
    - count_tokens_chat(): Exact token count
    - trim_text_to_token_limit_chat(): Trim to token budget
    - trim_history_preserve_messages_chat(): Trim preserving turn boundaries

Tool Model Functions (use TOOL_MODEL tokenizer):
    - count_tokens_tool(): Exact token count
    - trim_text_to_token_limit_tool(): Trim to token budget
    - trim_history_preserve_messages_tool(): Trim preserving turn boundaries
    - build_user_history_for_tool(): Format user-only history for classifier

Token counting is critical for staying within model context limits and
managing GPU memory usage (KV cache sizing).
"""

from .prefix import count_prefix_tokens, strip_screen_prefix, get_effective_user_utt_max_tokens
from .utils import (  # Chat-specific; Tool-specific
    count_tokens_chat,
    count_tokens_tool,
    build_user_history_for_tool,
    trim_text_to_token_limit_chat,
    trim_text_to_token_limit_tool,
    trim_history_preserve_messages_chat,
    trim_history_preserve_messages_tool,
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
    "build_user_history_for_tool",
    # Prefix
    "count_prefix_tokens",
    "strip_screen_prefix",
    "get_effective_user_utt_max_tokens",
]
