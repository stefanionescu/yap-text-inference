"""History parsing utilities for converting client payloads into runtime state."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from src.state.session import ChatMessage, HistoryTurn


def _validate_message_item(item: object) -> tuple[str, str] | None:
    """Validate one client history item and return ``(role, content)``."""
    if not isinstance(item, dict):
        return None
    role = item.get("role")
    content = item.get("content")
    if not isinstance(role, str) or not isinstance(content, str):
        return None
    normalized_role = role.strip().lower()
    normalized_content = content.strip()
    if not normalized_role or not normalized_content:
        return None
    return normalized_role, normalized_content


def _append_chat_message(messages: list[ChatMessage], role: str, content: str) -> None:
    normalized_content = content.strip()
    if role not in {"user", "assistant"} or not normalized_content:
        return
    if role == "user" and messages and messages[-1].role == "user":
        messages[-1].content = f"{messages[-1].content}\n\n{normalized_content}"
        return
    messages.append(ChatMessage(role=role, content=normalized_content))


def parse_history_text(history_text: str) -> list[ChatMessage]:
    """Parse a transcript string back into canonical chat messages."""
    text = (history_text or "").strip()
    if not text:
        return []

    messages: list[ChatMessage] = []
    current_role: str | None = None
    current_lines: list[str] = []

    def _flush() -> None:
        nonlocal current_role, current_lines
        if current_role is None or not current_lines:
            current_role = None
            current_lines = []
            return
        _append_chat_message(messages, current_role, "\n".join(current_lines).strip())
        current_role = None
        current_lines = []

    for line in text.splitlines():
        if line.startswith("User:"):
            _flush()
            current_role = "user"
            current_lines = [line[5:].lstrip()]
        elif line.startswith("Assistant:"):
            _flush()
            current_role = "assistant"
            current_lines = [line[10:].lstrip()]
        elif current_role is not None:
            current_lines.append(line)
        elif line.strip():
            current_role = "user"
            current_lines = [line]

    _flush()
    return messages


def parse_history_for_tool(messages: Sequence[object]) -> list[HistoryTurn]:
    """Parse history for the tool model as user-only history entries."""
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


def parse_history_for_chat(messages: Sequence[object]) -> list[ChatMessage]:
    """Parse client history into canonical ordered chat messages."""
    if not messages:
        return []

    parsed: list[ChatMessage] = []
    for item in messages:
        validated = _validate_message_item(item)
        if validated is None:
            continue
        role, content = validated
        _append_chat_message(parsed, role, content)
    return parsed


def parse_history_as_tuples(history_text: str) -> list[tuple[str, str]]:
    """Convert a transcript string into legacy ``(user, assistant)`` pairs."""
    messages = parse_history_text(history_text)
    pairs: list[tuple[str, str]] = []
    pending_user = ""

    for message in messages:
        if message.role == "user":
            if pending_user:
                pairs.append((pending_user, ""))
            pending_user = message.content
            continue
        if pending_user:
            pairs.append((pending_user, message.content))
            pending_user = ""
        else:
            pairs.append(("", message.content))

    if pending_user:
        pairs.append((pending_user, ""))
    return pairs


__all__ = [
    "parse_history_text",
    "parse_history_for_tool",
    "parse_history_for_chat",
    "parse_history_as_tuples",
]
