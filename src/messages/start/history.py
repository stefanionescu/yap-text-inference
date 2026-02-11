"""History parsing and user utterance trimming helpers for start messages."""

from __future__ import annotations

from typing import Any

from src.handlers.session.manager import SessionHandler

from ...config import DEPLOY_CHAT, DEPLOY_TOOL
from ...handlers.session.parsing import parse_history_messages
from ...tokens import count_tokens_chat, count_tokens_tool, trim_text_to_token_limit_chat, trim_text_to_token_limit_tool


def resolve_history(
    session_handler: SessionHandler,
    session_id: str,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any] | None]:
    """Resolve and trim history payload into runtime text plus metadata."""
    history_messages = payload.get("history")
    if not isinstance(history_messages, list):
        return session_handler.get_history_text(session_id), None

    input_count = len(history_messages)
    parsed_turns = parse_history_messages(history_messages)
    input_turn_count = len(parsed_turns)
    rendered = session_handler.set_history_turns(session_id, parsed_turns)
    retained_count = session_handler.get_history_turn_count(session_id)
    history_tokens = _count_history_tokens(rendered)
    history_info = {
        "input_messages": input_count,
        "input_turns": input_turn_count,
        "retained_turns": retained_count,
        "trimmed": retained_count < input_turn_count,
        "history_tokens": history_tokens,
    }
    return rendered, history_info


def trim_user_utterance(session_handler: SessionHandler, session_id: str, user_utt: str) -> str:
    """Trim user utterance to token limit based on active deploy mode."""
    effective_max = session_handler.get_effective_user_utt_max_tokens(session_id, for_followup=False)
    if DEPLOY_CHAT:
        return trim_text_to_token_limit_chat(user_utt, max_tokens=effective_max, keep="start")
    if DEPLOY_TOOL:
        return trim_text_to_token_limit_tool(user_utt, max_tokens=effective_max, keep="start")
    return user_utt or ""


def _count_history_tokens(rendered: str) -> int:
    if not rendered:
        return 0
    if DEPLOY_CHAT:
        return count_tokens_chat(rendered)
    if DEPLOY_TOOL:
        return count_tokens_tool(rendered)
    return 0


__all__ = [
    "resolve_history",
    "trim_user_utterance",
]
