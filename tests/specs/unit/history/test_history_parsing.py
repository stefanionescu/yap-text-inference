"""Unit tests for history parsing helpers."""

from __future__ import annotations

from src.handlers.session.parsing import (
    parse_history_text,
    parse_history_for_chat,
    parse_history_for_tool,
    parse_history_as_tuples,
)


def test_parse_history_text_preserves_multiline_sections() -> None:
    history_text = "User: hello\nAssistant: line one\nline two\nUser: second\nextra line\nAssistant: done"

    turns = parse_history_text(history_text)

    assert len(turns) == 2
    assert turns[0].user == "hello"
    assert turns[0].assistant == "line one\nline two"
    assert turns[1].user == "second\nextra line"
    assert turns[1].assistant == "done"


def test_parse_history_as_tuples_returns_ordered_pairs() -> None:
    history_text = "User: one\nAssistant: first\nUser: two\nAssistant: second"

    parsed = parse_history_as_tuples(history_text)

    assert parsed == [("one", "first"), ("two", "second")]


# --- parse_history_for_tool ---


def test_tool_each_user_msg_is_separate_turn() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u3"},
    ]
    turns = parse_history_for_tool(messages)
    assert len(turns) == 3
    assert turns[0].user == "u1"
    assert turns[0].assistant == ""
    assert turns[1].user == "u2"
    assert turns[2].user == "u3"


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


# --- parse_history_for_chat ---


def test_chat_consecutive_users_combined() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "user", "content": "u2"},
        {"role": "assistant", "content": "a1"},
    ]
    turns = parse_history_for_chat(messages)
    assert len(turns) == 1
    assert turns[0].user == "u1\n\nu2"
    assert turns[0].assistant == "a1"


def test_chat_consecutive_assistants_not_combined() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "assistant", "content": "a2"},
    ]
    turns = parse_history_for_chat(messages)
    assert len(turns) == 2
    assert turns[0].user == "u1"
    assert turns[0].assistant == "a1"
    assert turns[1].user == ""
    assert turns[1].assistant == "a2"


def test_chat_drops_non_user_assistant_roles() -> None:
    messages = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "u1"},
        {"role": "function", "content": "fn"},
        {"role": "assistant", "content": "a1"},
    ]
    turns = parse_history_for_chat(messages)
    assert len(turns) == 1
    assert turns[0].user == "u1"
    assert turns[0].assistant == "a1"


def test_chat_validates_items() -> None:
    messages = [
        42,
        {"role": "user"},
        {"content": "no role"},
        {"role": "user", "content": "valid"},
        {"role": "assistant", "content": "reply"},
    ]
    turns = parse_history_for_chat(messages)
    assert len(turns) == 1
    assert turns[0].user == "valid"
    assert turns[0].assistant == "reply"


def test_chat_trailing_user_flushed() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    turns = parse_history_for_chat(messages)
    assert len(turns) == 2
    assert turns[0].user == "u1"
    assert turns[0].assistant == "a1"
    assert turns[1].user == "u2"
    assert turns[1].assistant == ""


def test_chat_empty_list() -> None:
    assert parse_history_for_chat([]) == []
