"""Pure helpers for working with stored chat history as whole turns."""

from __future__ import annotations

from collections.abc import Sequence
from src.state.session import ChatMessage


def copy_chat_messages(messages: Sequence[ChatMessage]) -> list[ChatMessage]:
    """Return normalized copies of non-empty chat messages."""
    copied: list[ChatMessage] = []
    for message in messages:
        content = (message.content or "").strip()
        if not content:
            continue
        copied.append(ChatMessage(role=message.role, content=content))
    return copied


def group_chat_turns(messages: Sequence[ChatMessage]) -> list[list[ChatMessage]]:
    """Group chat messages into trim-safe turns.

    A turn starts with a user message and keeps any following assistant
    messages until the next user. Leading assistant-only messages are grouped
    together so trimming can still drop them as a unit.
    """

    turns: list[list[ChatMessage]] = []
    current_turn: list[ChatMessage] | None = None
    leading_assistants: list[ChatMessage] = []

    for message in copy_chat_messages(messages):
        if message.role == "user":
            if leading_assistants:
                turns.append(leading_assistants)
                leading_assistants = []
            if current_turn is not None:
                turns.append(current_turn)
            current_turn = [message]
            continue

        if current_turn is None:
            leading_assistants.append(message)
            continue

        current_turn.append(message)

    if leading_assistants:
        turns.append(leading_assistants)
    if current_turn is not None:
        turns.append(current_turn)

    return turns


def flatten_chat_turns(turns: Sequence[Sequence[ChatMessage]]) -> list[ChatMessage]:
    """Flatten grouped turns back into normalized chat messages."""
    return copy_chat_messages([message for turn in turns for message in turn])


__all__ = [
    "copy_chat_messages",
    "group_chat_turns",
    "flatten_chat_turns",
]
