"""History parsing and user utterance trimming helpers for start messages."""

from __future__ import annotations

from typing import Any
from src.state.session import SessionState
from ...config import DEPLOY_CHAT, DEPLOY_TOOL
from src.handlers.session.manager import SessionHandler
from ...tokens import trim_text_to_token_limit_chat, trim_text_to_token_limit_tool
from ...handlers.session.parsing import parse_history_for_chat, parse_history_for_tool


def resolve_history(
    session_handler: SessionHandler,
    state: SessionState,
    msg: dict[str, Any],
) -> str:
    """Resolve and trim history payload into runtime text.

    History is only accepted when the session has no turns yet.
    Uses mode-specific parsing: parse_history_for_tool for tool-only,
    parse_history_for_chat otherwise.
    """
    if session_handler.get_history_turn_count(state) > 0:
        return session_handler.get_history_text(state)

    history_messages = msg.get("history")
    if not isinstance(history_messages, list):
        return session_handler.get_history_text(state)

    if DEPLOY_TOOL and not DEPLOY_CHAT:
        parsed_turns = parse_history_for_tool(history_messages)
    else:
        parsed_turns = parse_history_for_chat(history_messages)

    session_handler.set_history_turns(state, parsed_turns)
    return session_handler.get_history_text(state)


def trim_user_utterance(session_handler: SessionHandler, state: SessionState, user_utt: str) -> str:
    """Trim user utterance to token limit based on active deploy mode."""
    effective_max = session_handler.get_effective_user_utt_max_tokens(state, for_followup=False)
    if DEPLOY_CHAT:
        return trim_text_to_token_limit_chat(user_utt, max_tokens=effective_max, keep="start")
    if DEPLOY_TOOL:
        return trim_text_to_token_limit_tool(user_utt, max_tokens=effective_max, keep="start")
    return user_utt or ""


__all__ = [
    "resolve_history",
    "trim_user_utterance",
]
