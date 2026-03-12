"""Shared realistic unit-test message samples."""

from __future__ import annotations

from src.state.session import ChatMessage

CHAT_MESSAGES: list[ChatMessage] = [
    ChatMessage(
        role="user",
        content="hello can you help me plan a trip to lisbon next week",
    ),
    ChatMessage(
        role="assistant",
        content="sure tell me your budget and hotel area preference",
    ),
    ChatMessage(
        role="user",
        content="i need a quiet hotel near the river and my budget is moderate",
    ),
    ChatMessage(
        role="assistant",
        content="a quiet riverside hotel in lisbon can work and i can suggest neighborhoods",
    ),
    ChatMessage(
        role="user",
        content="also remind me to pack a rain jacket and travel adapter",
    ),
    ChatMessage(
        role="assistant",
        content="i will keep weather and transit options in mind for that trip",
    ),
]


HISTORY_PAYLOAD: list[dict[str, str]] = [
    {"role": message.role, "content": message.content} for message in CHAT_MESSAGES
]


ASSISTANT_FIRST_MESSAGES: list[ChatMessage] = [
    ChatMessage(
        role="assistant",
        content="hello can you help me plan a trip to lisbon next week",
    ),
    ChatMessage(
        role="assistant",
        content="sure tell me your budget and hotel area preference",
    ),
    ChatMessage(
        role="user",
        content="i need a quiet hotel near the river and my budget is moderate",
    ),
    ChatMessage(
        role="assistant",
        content="a quiet riverside hotel in lisbon can work and i can suggest neighborhoods",
    ),
    ChatMessage(
        role="user",
        content="also remind me to pack a rain jacket and travel adapter",
    ),
    ChatMessage(
        role="assistant",
        content="i will keep weather and transit options in mind for that trip",
    ),
]


ASSISTANT_FIRST_PAYLOAD: list[dict[str, str]] = [
    {"role": message.role, "content": message.content} for message in ASSISTANT_FIRST_MESSAGES
]


TOOL_HISTORY: list[str] = [
    "check the calendar for next tuesday flight times",
    "show the booking confirmation and hotel address",
    "open the packing list and weather notes for lisbon",
]


def tool_turn_payloads() -> list[dict[str, str]]:
    """Build a start-message history payload from the realistic user turns."""
    return [{"role": "user", "content": text} for text in TOOL_HISTORY]


__all__ = [
    "ASSISTANT_FIRST_MESSAGES",
    "ASSISTANT_FIRST_PAYLOAD",
    "CHAT_MESSAGES",
    "HISTORY_PAYLOAD",
    "TOOL_HISTORY",
    "tool_turn_payloads",
]
