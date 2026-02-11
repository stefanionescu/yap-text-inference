"""History parsing utilities for converting between formats.

This module handles parsing conversation history from various input formats
into structured HistoryTurn objects. It supports:

1. Text parsing: "User: X\nAssistant: Y" format
2. JSON parsing: [{role: "user", content: "..."}, ...] format
3. Tuple conversion: For prompt builders that need (user, assistant) tuples
"""

from __future__ import annotations

import uuid

from src.state.session import HistoryTurn


def parse_history_text(history_text: str) -> list[HistoryTurn]:
    """Parse text transcript back into structured HistoryTurn objects.

    Handles multi-line messages by accumulating lines until the next
    role marker (User: or Assistant:) is encountered.

    Args:
        history_text: Raw history in "User: X\\nAssistant: Y" format.

    Returns:
        List of HistoryTurn objects with generated UUIDs.
    """
    text = (history_text or "").strip()
    if not text:
        return []

    turns: list[HistoryTurn] = []
    current_user: list[str] = []
    current_assistant: list[str] = []
    mode: str | None = None

    def _flush() -> None:
        nonlocal current_user, current_assistant, mode
        if not current_user and not current_assistant:
            return
        turns.append(
            HistoryTurn(
                turn_id=uuid.uuid4().hex,
                user="\n".join(current_user).strip(),
                assistant="\n".join(current_assistant).strip(),
            )
        )
        current_user, current_assistant, mode = [], [], None

    for line in text.splitlines():
        if line.startswith("User:"):
            _flush()
            current_user = [line[5:].lstrip()]
            mode = "user"
        elif line.startswith("Assistant:"):
            current_assistant = [line[10:].lstrip()]
            mode = "assistant"
        elif mode == "assistant":
            current_assistant.append(line)
        elif mode == "user":
            current_user.append(line)
        elif line.strip():
            current_user.append(line)
            mode = "user"
    _flush()
    return turns


def parse_history_messages(messages: list[dict]) -> list[HistoryTurn]:
    """Parse JSON message array into structured HistoryTurn objects.

    Accepts the standard chat format: [{role: "user", content: "..."}, ...]
    Groups consecutive user/assistant messages into turns.

    Args:
        messages: List of {role, content} dicts. Role must be "user" or "assistant".

    Returns:
        List of HistoryTurn objects with generated UUIDs.
    """
    if not messages:
        return []

    turns: list[HistoryTurn] = []
    current_user: list[str] = []
    current_assistant: list[str] = []

    def _flush() -> None:
        nonlocal current_user, current_assistant
        if not current_user and not current_assistant:
            return
        turns.append(
            HistoryTurn(
                turn_id=uuid.uuid4().hex,
                user="\n\n".join(current_user).strip(),
                assistant="\n\n".join(current_assistant).strip(),
            )
        )
        current_user, current_assistant = [], []

    for msg in messages:
        role = msg.get("role", "").lower().strip()
        content = (msg.get("content") or "").strip()
        if not content:
            continue

        if role == "user":
            # If we have assistant content, flush the turn before starting new user
            if current_assistant:
                _flush()
            current_user.append(content)
        elif role == "assistant":
            current_assistant.append(content)

    _flush()
    return turns


def parse_history_as_tuples(history_text: str) -> list[tuple[str, str]]:
    """Parse history text into (user, assistant) tuples.

    This is a convenience wrapper around parse_history_text for callers
    that need the simpler tuple format (e.g., prompt builders).

    Args:
        history_text: Raw history in "User: X\nAssistant: Y" format

    Returns:
        List of (user_text, assistant_text) tuples
    """
    turns = parse_history_text(history_text)
    return [(turn.user, turn.assistant) for turn in turns]


__all__ = [
    "parse_history_text",
    "parse_history_messages",
    "parse_history_as_tuples",
]
