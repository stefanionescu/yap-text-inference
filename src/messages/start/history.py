"""History parsing and user utterance trimming helpers for start messages."""

from __future__ import annotations

from typing import Any
from ...config import DEPLOY_CHAT, DEPLOY_TOOL
from src.handlers.session.manager import SessionHandler
from src.state.session import HistoryTurn, SessionState
from ...handlers.session.parsing import parse_history_for_chat, parse_history_for_tool


def _history_turn_count(state: SessionState) -> int:
    if state.history_turns is not None:
        return len(state.history_turns)
    if state.tool_history_turns is not None:
        return len(state.tool_history_turns)
    return 0


def resolve_history(
    session_handler: SessionHandler,
    state: SessionState,
    msg: dict[str, Any],
) -> list[HistoryTurn]:
    """Resolve and trim history payload into runtime text.

    History is only accepted when the session has no turns yet.
    Uses mode-specific parsing: parse_history_for_tool for tool-only,
    parse_history_for_chat otherwise.
    """
    if _history_turn_count(state) > 0:
        return session_handler._history.get_turns(state)

    history_messages = msg.get("history")
    if not isinstance(history_messages, list):
        return session_handler._history.get_turns(state)

    if DEPLOY_CHAT and DEPLOY_TOOL:
        chat_turns = parse_history_for_chat(history_messages)
        tool_turns = parse_history_for_tool(history_messages)
        session_handler._history.set_mode_turns(state, chat_turns=chat_turns, tool_turns=tool_turns)
    elif DEPLOY_TOOL and not DEPLOY_CHAT:
        tool_turns = parse_history_for_tool(history_messages)
        session_handler._history.set_mode_turns(state, tool_turns=tool_turns)
    else:
        chat_turns = parse_history_for_chat(history_messages)
        session_handler._history.set_mode_turns(state, chat_turns=chat_turns)
    return session_handler._history.get_turns(state)


def trim_chat_user_utterance(
    session_handler: SessionHandler,
    state: SessionState,
    chat_user_utt: str,
    *,
    for_followup: bool = False,
) -> str:
    """Trim chat user utterance to chat-side token limit."""
    effective_max = session_handler.get_effective_chat_user_utt_max_tokens(state, for_followup=for_followup)
    if DEPLOY_CHAT:
        return session_handler.trim_chat_user_utterance(chat_user_utt, max_tokens=effective_max)
    return chat_user_utt or ""


def trim_tool_user_utterance(
    session_handler: SessionHandler,
    tool_user_utt: str,
) -> str:
    """Trim user utterance to tool-side token limit."""
    effective_max = session_handler.get_effective_tool_user_utt_max_tokens()
    if DEPLOY_TOOL:
        return session_handler.trim_tool_user_utterance(tool_user_utt, max_tokens=effective_max)
    return tool_user_utt or ""


def resolve_user_utterances(
    session_handler: SessionHandler,
    state: SessionState,
    incoming_user_utt: str,
    *,
    for_followup: bool = False,
) -> tuple[str, str]:
    """Resolve chat/tool utterance variants with independent trimming rules."""
    raw = incoming_user_utt or ""
    chat_user = (
        trim_chat_user_utterance(session_handler, state, raw, for_followup=for_followup) if DEPLOY_CHAT else raw
    )
    tool_user = trim_tool_user_utterance(session_handler, raw) if DEPLOY_TOOL else raw
    return chat_user, tool_user


__all__ = [
    "resolve_history",
    "trim_chat_user_utterance",
    "trim_tool_user_utterance",
    "resolve_user_utterances",
]
