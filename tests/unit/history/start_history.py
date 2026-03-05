"""Unit tests for start-message history/token accounting helpers."""

from __future__ import annotations

import pytest
from src.tokens import count_tokens_chat
from src.state.session import SessionState
import src.messages.start.history as start_history
import src.handlers.session.history as session_history
from src.handlers.session.manager import SessionHandler
from tests.helpers.tokenizer import use_local_tokenizers


def _build_session_handler(monkeypatch: pytest.MonkeyPatch) -> SessionHandler:
    monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 1000)
    monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 800)
    monkeypatch.setattr(session_history, "TOOL_HISTORY_TOKENS", 800)
    monkeypatch.setattr(session_history, "DEPLOY_CHAT", True)
    monkeypatch.setattr(session_history, "DEPLOY_TOOL", False)
    monkeypatch.setattr(start_history, "DEPLOY_CHAT", True)
    monkeypatch.setattr(start_history, "DEPLOY_TOOL", False)
    return SessionHandler(chat_engine=None)


def _make_state(handler: SessionHandler) -> SessionState:
    state = SessionState(meta={})
    handler.initialize_session(state)
    return state


def test_resolve_history_renders_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        handler = _build_session_handler(monkeypatch)
        state = _make_state(handler)
        msg = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "how are you"},
                {"role": "assistant", "content": "great"},
            ]
        }

        rendered = start_history.resolve_history(handler, state, msg)

        assert "User: hello" in rendered
        assert "Assistant: great" in rendered


def test_resolve_history_trims_when_over_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with use_local_tokenizers():
        handler = _build_session_handler(monkeypatch)
        monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 6)
        monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 4)

        state = _make_state(handler)
        msg = {
            "history": [
                {"role": "user", "content": "u1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "u2"},
                {"role": "assistant", "content": "a2"},
                {"role": "user", "content": "u3"},
                {"role": "assistant", "content": "a3"},
            ]
        }

        rendered = start_history.resolve_history(handler, state, msg)

        # Some turns should have been trimmed; not all 3 turns kept
        assert len(state.history_turns) < 3
        assert isinstance(rendered, str)


def test_trim_user_utterance_uses_effective_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with use_local_tokenizers():
        handler = _build_session_handler(monkeypatch)
        state = _make_state(handler)

        monkeypatch.setattr(start_history, "DEPLOY_CHAT", True)
        monkeypatch.setattr(start_history, "DEPLOY_TOOL", False)
        monkeypatch.setattr(
            handler,
            "get_effective_user_utt_max_tokens",
            lambda _state, *, for_followup=False: 5,
        )

        trimmed = start_history.trim_user_utterance(handler, state, "alpha bravo charlie")
        assert count_tokens_chat(trimmed) <= 5


def test_resolve_history_allows_seed_on_fresh_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh session with 0 turns accepts client-sent history."""
    with use_local_tokenizers():
        handler = _build_session_handler(monkeypatch)
        state = _make_state(handler)

        assert handler.get_history_turn_count(state) == 0

        msg = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
        }

        rendered = start_history.resolve_history(handler, state, msg)

        assert "hello" in rendered
        assert handler.get_history_turn_count(state) == 1


def test_resolve_history_ignores_history_after_first_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: if a session already has turns, client-sent history is ignored."""
    with use_local_tokenizers():
        handler = _build_session_handler(monkeypatch)
        state = _make_state(handler)

        # Seed history on fresh session (first request).
        seed_msg = {
            "history": [
                {"role": "user", "content": "first hello"},
                {"role": "assistant", "content": "first hi"},
            ]
        }
        rendered_1 = start_history.resolve_history(handler, state, seed_msg)
        assert "first hello" in rendered_1

        # Simulate the server processing the first request — adds a turn.
        handler.append_user_utterance(state, "follow-up")
        assert handler.get_history_turn_count(state) > 0

        # Second request sends different history — should be ignored.
        second_msg = {
            "history": [
                {"role": "user", "content": "OVERWRITE ATTEMPT"},
                {"role": "assistant", "content": "OVERWRITE ATTEMPT"},
            ]
        }
        rendered_2 = start_history.resolve_history(handler, state, second_msg)

        # Guard should return early and preserve accumulated history.
        assert "OVERWRITE ATTEMPT" not in rendered_2
        assert "first hello" in rendered_2
