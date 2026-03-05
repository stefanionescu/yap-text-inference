"""History parsing utilities for converting between formats.

This module handles parsing conversation history from various input formats
into structured HistoryTurn objects. It supports:

1. Text parsing: "User: X\nAssistant: Y" format
2. JSON parsing: [{role: "user", content: "..."}, ...] format
3. Tuple conversion: For prompt builders that need (user, assistant) tuples
"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from src.state.session import HistoryTurn


def _validate_message_item(item: object) -> tuple[str, str] | None:
    """Validate a single history message item.

    Returns (role, content) if valid, None otherwise.
    """
    if not isinstance(item, dict):
        return None
    role = item.get("role")
    content = item.get("content")
    if not isinstance(role, str) or not isinstance(content, str):
        return None
    role = role.strip().lower()
    content = content.strip()
    if not role or not content:
        return None
    return role, content


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


def parse_history_for_tool(messages: Sequence[object]) -> list[HistoryTurn]:
    """Parse history for the tool model: each user message becomes a separate turn.

    Non-user roles are dropped. Assistant text is set to empty string.
    Each item is validated: must be dict with string role and string content.

    Args:
        messages: List of message dicts (or invalid items to be skipped).

    Returns:
        List of HistoryTurn objects, one per valid user message.
    """
    if not messages:
        return []

    turns: list[HistoryTurn] = []
    for item in messages:
        validated = _validate_message_item(item)
        if validated is None:
            continue
        role, content = validated
        if role != "user":
            continue
        turns.append(
            HistoryTurn(
                turn_id=uuid.uuid4().hex,
                user=content,
                assistant="",
            )
        )
    return turns


def parse_history_for_chat(messages: Sequence[object]) -> list[HistoryTurn]:
    """Parse history for the chat model.

    - Consecutive user messages are combined into one turn.
    - Consecutive assistant messages are NOT combined; each gets its own turn
      with an empty user string.
    - Non-user/assistant roles are dropped.
    - Each item is validated: must be dict with string role and string content.

    Args:
        messages: List of message dicts (or invalid items to be skipped).

    Returns:
        List of HistoryTurn objects.
    """
    if not messages:
        return []

    turns: list[HistoryTurn] = []
    current_user_parts: list[str] = []

    def _flush_user() -> None:
        nonlocal current_user_parts
        if current_user_parts:
            turns.append(
                HistoryTurn(
                    turn_id=uuid.uuid4().hex,
                    user="\n\n".join(current_user_parts),
                    assistant="",
                )
            )
            current_user_parts = []

    for item in messages:
        validated = _validate_message_item(item)
        if validated is None:
            continue
        role, content = validated
        if role == "user":
            current_user_parts.append(content)
        elif role == "assistant":
            # If there are accumulated user parts, create a turn with this assistant response
            if current_user_parts:
                turns.append(
                    HistoryTurn(
                        turn_id=uuid.uuid4().hex,
                        user="\n\n".join(current_user_parts),
                        assistant=content,
                    )
                )
                current_user_parts = []
            else:
                # Consecutive assistant: own turn with empty user
                turns.append(
                    HistoryTurn(
                        turn_id=uuid.uuid4().hex,
                        user="",
                        assistant=content,
                    )
                )

    # Flush any remaining user parts
    _flush_user()
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
    "parse_history_for_tool",
    "parse_history_for_chat",
    "parse_history_as_tuples",
]
