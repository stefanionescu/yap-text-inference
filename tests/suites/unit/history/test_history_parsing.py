"""Unit tests for history parsing helpers."""

from __future__ import annotations

from tests.support.messages.unit import ASSISTANT_FIRST_PAYLOAD, ASSISTANT_FIRST_MESSAGES
from src.handlers.session.parsing import (
    parse_history_text,
    parse_history_for_chat,
    parse_history_for_tool,
    parse_history_as_tuples,
)


def test_parse_history_text_preserves_multiline_sections() -> None:
    history_text = (
        "User: hello can you help me plan a trip\n"
        "Assistant: sure tell me your budget\n"
        "and hotel area\n"
        "User: i need a quiet hotel\n"
        "near the river\n"
        "Assistant: great"
    )

    messages = parse_history_text(history_text)

    assert [(message.role, message.content) for message in messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget\nand hotel area"),
        ("user", "i need a quiet hotel\nnear the river"),
        ("assistant", "great"),
    ]


def test_parse_history_as_tuples_returns_ordered_pairs() -> None:
    history_text = (
        "User: hello can you help me plan a trip\n"
        "Assistant: sure tell me your budget\n"
        "User: i need a quiet hotel near the river\n"
        "Assistant: great"
    )

    parsed = parse_history_as_tuples(history_text)

    assert parsed == [
        ("hello can you help me plan a trip", "sure tell me your budget"),
        ("i need a quiet hotel near the river", "great"),
    ]


def test_parse_history_as_tuples_preserves_leading_assistant_sections() -> None:
    history_text = (
        "Assistant: hello can you help me plan a trip to lisbon next week\n"
        "Assistant: sure tell me your budget and hotel area preference\n"
        "User: i need a quiet hotel near the river and my budget is moderate\n"
        "Assistant: a quiet riverside hotel in lisbon can work and i can suggest neighborhoods\n"
        "User: also remind me to pack a rain jacket and travel adapter\n"
        "Assistant: i will keep weather and transit options in mind for that trip"
    )

    parsed = parse_history_as_tuples(history_text)

    assert parsed == [
        ("", "hello can you help me plan a trip to lisbon next week"),
        ("", "sure tell me your budget and hotel area preference"),
        (
            "i need a quiet hotel near the river and my budget is moderate",
            "a quiet riverside hotel in lisbon can work and i can suggest neighborhoods",
        ),
        (
            "also remind me to pack a rain jacket and travel adapter",
            "i will keep weather and transit options in mind for that trip",
        ),
    ]


def test_tool_each_user_msg_is_separate_turn() -> None:
    messages = [
        {"role": "user", "content": "check the calendar for next tuesday flight times"},
        {"role": "user", "content": "show the booking confirmation and hotel address"},
        {"role": "assistant", "content": "ignored"},
        {"role": "user", "content": "open the packing list and weather notes for lisbon"},
    ]
    turns = parse_history_for_tool(messages)
    assert len(turns) == 3
    assert turns[0].user == "check the calendar for next tuesday flight times"
    assert turns[0].assistant == ""
    assert turns[1].user == "show the booking confirmation and hotel address"
    assert turns[2].user == "open the packing list and weather notes for lisbon"


def test_tool_drops_non_user_roles() -> None:
    messages = [
        {"role": "assistant", "content": "a1"},
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
    ]
    turns = parse_history_for_tool(messages)
    assert len(turns) == 1
    assert turns[0].user == "u1"


def test_tool_validates_items() -> None:
    messages = [
        "not a dict",
        {"role": 123, "content": "bad role"},
        {"role": "user", "content": 456},
        {"role": "user", "content": ""},
        {"role": "user", "content": "valid"},
    ]
    turns = parse_history_for_tool(messages)
    assert len(turns) == 1
    assert turns[0].user == "valid"


def test_tool_empty_list() -> None:
    assert parse_history_for_tool([]) == []


def test_chat_consecutive_users_combined() -> None:
    messages = [
        {"role": "user", "content": "hello can you help me plan a trip"},
        {"role": "user", "content": "i need a quiet hotel near the river"},
        {"role": "assistant", "content": "sure tell me your budget"},
    ]
    parsed = parse_history_for_chat(messages)
    assert [(message.role, message.content) for message in parsed] == [
        ("user", "hello can you help me plan a trip\n\ni need a quiet hotel near the river"),
        ("assistant", "sure tell me your budget"),
    ]


def test_chat_consecutive_assistants_not_combined() -> None:
    messages = [
        {"role": "user", "content": "hello can you help me plan a trip"},
        {"role": "assistant", "content": "sure tell me your budget"},
        {"role": "assistant", "content": "and hotel area"},
    ]
    parsed = parse_history_for_chat(messages)
    assert [(message.role, message.content) for message in parsed] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget"),
        ("assistant", "and hotel area"),
    ]


def test_chat_preserves_assistant_first_history_in_order() -> None:
    parsed = parse_history_for_chat(ASSISTANT_FIRST_PAYLOAD)

    assert parsed == ASSISTANT_FIRST_MESSAGES


def test_chat_drops_non_user_assistant_roles() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "function", "content": "fn"},
        {"role": "assistant", "content": "a1"},
    ]
    parsed = parse_history_for_chat(messages)
    assert [(message.role, message.content) for message in parsed] == [
        ("user", "u1"),
        ("assistant", "a1"),
    ]


def test_chat_validates_items() -> None:
    messages = [
        42,
        {"role": "user"},
        {"content": "no role"},
        {"role": "user", "content": "valid"},
        {"role": "assistant", "content": "reply"},
    ]
    parsed = parse_history_for_chat(messages)
    assert [(message.role, message.content) for message in parsed] == [
        ("user", "valid"),
        ("assistant", "reply"),
    ]


def test_chat_trailing_user_preserved_as_user_message() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    parsed = parse_history_for_chat(messages)
    assert [(message.role, message.content) for message in parsed] == [
        ("user", "u1"),
        ("assistant", "a1"),
        ("user", "u2"),
    ]


def test_chat_empty_list() -> None:
    assert parse_history_for_chat([]) == []
