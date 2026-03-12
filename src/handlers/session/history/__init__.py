"""Session history package with explicit runtime configuration."""

from .controller import HistoryController
from .settings import HistoryRuntimeConfig, build_history_runtime_config
from src.tokens.history import count_chat_tokens, count_tool_tokens, build_tool_history
from .ops import get_user_texts, render_history, trim_chat_history, trim_tool_history, render_tool_history_text

__all__ = [
    "HistoryRuntimeConfig",
    "build_history_runtime_config",
    "render_history",
    "trim_chat_history",
    "trim_tool_history",
    "render_tool_history_text",
    "get_user_texts",
    "count_chat_tokens",
    "count_tool_tokens",
    "build_tool_history",
    "HistoryController",
]
