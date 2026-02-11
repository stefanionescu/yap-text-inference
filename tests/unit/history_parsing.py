"""Unit tests for history parsing helpers."""

from __future__ import annotations

from src.handlers.session.parsing import parse_history_text, parse_history_messages, parse_history_as_tuples


def test_parse_history_messages_groups_consecutive_roles() -> None:
    messages = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "assistant", "content": "a1b"},
        {"role": "user", "content": "u2"},
        {"role": "user", "content": "u2b"},
        {"role": "assistant", "content": "a2"},
        {"role": "system", "content": "ignored"},
        {"role": "assistant", "content": "   "},
    ]

    turns = parse_history_messages(messages)

    assert len(turns) == 2
    assert turns[0].user == "u1"
    assert turns[0].assistant == "a1\n\na1b"
    assert turns[1].user == "u2\n\nu2b"
    assert turns[1].assistant == "a2"


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
