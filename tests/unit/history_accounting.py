"""Unit tests for session history update/accounting behavior."""

from __future__ import annotations

import pytest

from src.state.session import HistoryTurn
import src.handlers.session.history as session_history
from src.handlers.session.manager import SessionHandler
from tests.unit.local_tokenizer import use_local_tokenizers


def _build_session_handler(monkeypatch: pytest.MonkeyPatch) -> SessionHandler:
    monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 1000)
    monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 800)
    monkeypatch.setattr(session_history, "TOOL_HISTORY_TOKENS", 800)
    return SessionHandler(chat_engine=None)


def test_append_history_turn_updates_existing_turn_when_turn_id_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-update"
        session_handler.initialize_session(session_id)

        turn_id = session_handler.append_user_utterance(session_id, "hello")
        assert turn_id is not None
        assert session_handler.get_history_turn_count(session_id) == 1

        session_handler.append_history_turn(session_id, "ignored", "world", turn_id=turn_id)
        rendered = session_handler.get_history_text(session_id)

        assert session_handler.get_history_turn_count(session_id) == 1
        assert "User: hello" in rendered
        assert "Assistant: world" in rendered


def test_set_history_turns_keeps_expected_turn_count(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-import"
        session_handler.initialize_session(session_id)

        turns = [
            HistoryTurn(turn_id="t1", user="u1", assistant="a1"),
            HistoryTurn(turn_id="t2", user="u2", assistant="a2"),
        ]

        rendered = session_handler.set_history_turns(session_id, turns)

        assert "User: u1" in rendered
        assert "Assistant: a2" in rendered
        assert session_handler.get_history_turn_count(session_id) == 2
