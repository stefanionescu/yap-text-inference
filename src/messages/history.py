"""Shared history parsing and user-utterance normalization helpers."""

from __future__ import annotations

from typing import Any
from src.handlers.session.manager import SessionHandler
from src.state.session import ChatMessage, SessionState
from src.handlers.session.parsing import parse_history_for_chat, parse_history_for_tool


def _history_turn_count(state: SessionState) -> int:
    if state.chat_history_messages is not None:
        return len(state.chat_history_messages)
    if state.tool_history_turns is not None:
        return len(state.tool_history_turns)
    return 0


def resolve_history(
    session_handler: SessionHandler,
    state: SessionState,
    msg: dict[str, Any],
) -> list[ChatMessage]:
    """Resolve and trim history payload into runtime state.

    History is only accepted when the session has no turns yet.
    Uses mode-specific parsing: parse_history_for_tool for tool-only,
    parse_history_for_chat otherwise.
    """
    if _history_turn_count(state) > 0:
        return session_handler.get_chat_messages(state)

    history_messages = msg.get("history")
    if not isinstance(history_messages, list):
        return session_handler.get_chat_messages(state)

    history_config = session_handler.history_config
    if history_config.deploy_chat and history_config.deploy_tool:
        chat_messages = parse_history_for_chat(history_messages)
        tool_turns = parse_history_for_tool(history_messages)
        session_handler.set_mode_histories(state, chat_messages=chat_messages, tool_turns=tool_turns)
    elif history_config.deploy_tool and not history_config.deploy_chat:
        tool_turns = parse_history_for_tool(history_messages)
        session_handler.set_mode_histories(state, tool_turns=tool_turns)
    else:
        chat_messages = parse_history_for_chat(history_messages)
        session_handler.set_mode_histories(state, chat_messages=chat_messages)
    return session_handler.get_chat_messages(state)


def resolve_user_utterances(
    session_handler: SessionHandler,
    state: SessionState,
    incoming_user_utt: str,
) -> tuple[str, str]:
    """Normalize chat/tool utterance variants without mutating history."""
    raw = incoming_user_utt or ""
    history_config = session_handler.history_config
    chat_user, tool_user = session_handler.normalize_user_utterances(
        state,
        raw,
        tool_user_utt=raw if history_config.deploy_tool else None,
    )
    resolved_chat_user = chat_user if history_config.deploy_chat else raw
    resolved_tool_user = tool_user if tool_user is not None else resolved_chat_user
    return resolved_chat_user, resolved_tool_user


__all__ = [
    "resolve_history",
    "resolve_user_utterances",
]
