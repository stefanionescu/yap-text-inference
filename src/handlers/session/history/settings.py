"""Runtime configuration for session history behavior."""

from __future__ import annotations

from dataclasses import dataclass
from src.config.tool import TOOL_HISTORY_TOKENS
from src.config import DEPLOY_CHAT, DEPLOY_TOOL, TRIMMED_HISTORY_LENGTH, CHAT_HISTORY_MAX_TOKENS


@dataclass(frozen=True, slots=True)
class HistoryRuntimeConfig:
    """Runtime controls for history storage and trimming behavior."""

    deploy_chat: bool
    deploy_tool: bool
    chat_trigger_tokens: int
    chat_target_tokens: int
    default_tool_history_tokens: int | None = None


def build_history_runtime_config(
    *,
    deploy_chat: bool = DEPLOY_CHAT,
    deploy_tool: bool = DEPLOY_TOOL,
    chat_trigger_tokens: int = CHAT_HISTORY_MAX_TOKENS,
    chat_target_tokens: int = TRIMMED_HISTORY_LENGTH,
    default_tool_history_tokens: int | None = TOOL_HISTORY_TOKENS,
) -> HistoryRuntimeConfig:
    """Build a normalized history runtime config."""
    normalized_tool_tokens = None if default_tool_history_tokens is None else int(default_tool_history_tokens)
    return HistoryRuntimeConfig(
        deploy_chat=bool(deploy_chat),
        deploy_tool=bool(deploy_tool),
        chat_trigger_tokens=max(1, int(chat_trigger_tokens)),
        chat_target_tokens=max(1, int(chat_target_tokens)),
        default_tool_history_tokens=normalized_tool_tokens,
    )


__all__ = ["HistoryRuntimeConfig", "build_history_runtime_config"]
