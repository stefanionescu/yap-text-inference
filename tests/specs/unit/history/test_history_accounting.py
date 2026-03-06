"""Unit tests for session history update/accounting behavior."""

from __future__ import annotations

import pytest
from src.tokens import count_tokens_tool
import src.handlers.session.history as session_history
from src.handlers.session.manager import SessionHandler
from src.state.session import HistoryTurn, SessionState
from tests.support.helpers.tokenizer import use_local_tokenizers


def _build_session_handler(monkeypatch: pytest.MonkeyPatch) -> SessionHandler:
    monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 1000)
    monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 800)
    return SessionHandler(chat_engine=None)


def _make_state(handler: SessionHandler) -> SessionState:
    state = SessionState(meta={})
    handler.initialize_session(state)
    return state


def test_append_history_turn_updates_existing_turn_when_turn_id_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        state = _make_state(session_handler)

        turn_id = session_handler.append_user_utterance(state, "hello")
        assert turn_id is not None
        assert session_handler.get_history_turn_count(state) == 1

        session_handler.append_history_turn(state, "ignored", "world", turn_id=turn_id)
        rendered = session_handler.get_history_text(state)

        assert session_handler.get_history_turn_count(state) == 1
        assert "User: hello" in rendered
        assert "Assistant: world" in rendered


def test_set_history_turns_keeps_expected_turn_count(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        state = _make_state(session_handler)

        turns = [
            HistoryTurn(turn_id="t1", user="u1", assistant="a1"),
            HistoryTurn(turn_id="t2", user="u2", assistant="a2"),
        ]

        rendered = session_handler.set_history_turns(state, turns)

        assert "User: u1" in rendered
        assert "Assistant: a2" in rendered
        assert session_handler.get_history_turn_count(state) == 2


def test_render_tool_history_text_respects_explicit_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        monkeypatch.setattr(session_history, "DEPLOY_TOOL", True)
        turns = [HistoryTurn(turn_id="t1", user="one two three four five", assistant="")]
        rendered = session_history.render_tool_history_text(turns, max_tokens=3)
        assert rendered == "three four five"
        assert count_tokens_tool(rendered) <= 3


def _build_tool_only_handler(
    monkeypatch: pytest.MonkeyPatch,
    tool_budget: int = 10,
) -> SessionHandler:
    monkeypatch.setattr(session_history, "DEPLOY_CHAT", False)
    monkeypatch.setattr(session_history, "DEPLOY_TOOL", True)
    monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 1000)
    monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 800)
    return SessionHandler(chat_engine=None, tool_history_budget=tool_budget)


def test_trim_history_tool_only_drops_old_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool-only trim_tool_history drops oldest turns to stay within budget."""
    with use_local_tokenizers():
        _build_tool_only_handler(monkeypatch, tool_budget=10)
        state = SessionState(meta={})

        # Each user text is ~2-3 tokens; 5 turns should exceed budget of 10.
        turns = [HistoryTurn(turn_id=f"t{i}", user=f"word{i} extra{i} more{i}", assistant="") for i in range(5)]
        state.tool_history_turns = turns
        session_history.trim_tool_history(state, 6)

        assert len(state.tool_history_turns) < 5
        # Most recent turn is preserved
        assert state.tool_history_turns[-1].turn_id == "t4"


def test_trim_history_tool_only_clips_oversized_last_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool-only trim_tool_history clips a single oversized turn in-place."""
    with use_local_tokenizers():
        _build_tool_only_handler(monkeypatch, tool_budget=5)
        state = SessionState(meta={})

        long_text = "alpha bravo charlie delta echo foxtrot golf hotel india"
        state.tool_history_turns = [HistoryTurn(turn_id="t1", user=long_text, assistant="")]
        session_history.trim_tool_history(state, 3)

        assert len(state.tool_history_turns) == 1
        clipped_text = state.tool_history_turns[0].user
        assert count_tokens_tool(clipped_text) <= 3


def test_trim_history_tool_only_noop_when_under_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool-only trim_tool_history is a no-op when under budget."""
    with use_local_tokenizers():
        _build_tool_only_handler(monkeypatch, tool_budget=100)
        state = SessionState(meta={})

        turns = [
            HistoryTurn(turn_id="t1", user="hi", assistant=""),
            HistoryTurn(turn_id="t2", user="hello", assistant=""),
        ]
        state.tool_history_turns = turns
        session_history.trim_tool_history(state, 100)

        assert len(state.tool_history_turns) == 2
