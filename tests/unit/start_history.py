"""Unit tests for start-message history/token accounting helpers."""

from __future__ import annotations

import pytest

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


def test_resolve_history_reports_exact_turn_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-metrics"
        session_handler.initialize_session(session_id)
        payload = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "how are you"},
                {"role": "assistant", "content": "great"},
            ]
        }

        rendered, history_info = start_history.resolve_history(session_handler, session_id, payload)

        assert "User: hello" in rendered
        assert "Assistant: great" in rendered
        assert history_info is not None
        assert history_info["input_messages"] == 4
        assert history_info["input_turns"] == 2
        assert history_info["retained_turns"] == 2
        assert history_info["trimmed"] is False
        assert history_info["history_tokens"] == start_history.count_tokens_chat(rendered)


def test_resolve_history_marks_trimmed_when_turns_are_dropped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        monkeypatch.setattr(session_history, "HISTORY_MAX_TOKENS", 6)
        monkeypatch.setattr(session_history, "TRIMMED_HISTORY_LENGTH", 4)

        session_id = "session-trimmed"
        session_handler.initialize_session(session_id)
        payload = {
            "history": [
                {"role": "user", "content": "u1"},
                {"role": "assistant", "content": "a1"},
                {"role": "user", "content": "u2"},
                {"role": "assistant", "content": "a2"},
                {"role": "user", "content": "u3"},
                {"role": "assistant", "content": "a3"},
            ]
        }

        _, history_info = start_history.resolve_history(session_handler, session_id, payload)

        assert history_info is not None
        assert history_info["input_turns"] == 3
        assert history_info["retained_turns"] < 3
        assert history_info["trimmed"] is True


def test_trim_user_utterance_uses_effective_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-utterance"
        session_handler.initialize_session(session_id)

        monkeypatch.setattr(start_history, "DEPLOY_CHAT", True)
        monkeypatch.setattr(start_history, "DEPLOY_TOOL", False)
        monkeypatch.setattr(
            session_handler,
            "get_effective_user_utt_max_tokens",
            lambda _sid, *, for_followup=False: 5,
        )

        trimmed = start_history.trim_user_utterance(session_handler, session_id, "alpha bravo charlie")
        assert start_history.count_tokens_chat(trimmed) <= 5


def test_resolve_history_allows_seed_on_fresh_session(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fresh session with 0 turns accepts client-sent history."""
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-fresh-seed"
        session_handler.initialize_session(session_id)

        assert session_handler.get_history_turn_count(session_id) == 0

        payload = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
        }

        rendered, history_info = start_history.resolve_history(session_handler, session_id, payload)

        assert "hello" in rendered
        assert history_info is not None
        assert history_info["input_messages"] == 2
        assert history_info["retained_turns"] == 1


def test_resolve_history_ignores_history_after_first_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """Guard: if a session already has turns, client-sent history is ignored.

    This scenario is unreachable in normal flow (start is once-per-connection)
    but tests the safety net in resolve_history.
    """
    with use_local_tokenizers():
        session_handler = _build_session_handler(monkeypatch)
        session_id = "session-ignore-resend"
        session_handler.initialize_session(session_id)

        # Seed history on fresh session (first request).
        seed_payload = {
            "history": [
                {"role": "user", "content": "first hello"},
                {"role": "assistant", "content": "first hi"},
            ]
        }
        rendered_1, info_1 = start_history.resolve_history(session_handler, session_id, seed_payload)
        assert info_1 is not None
        assert "first hello" in rendered_1

        # Simulate the server processing the first request — adds a turn.
        session_handler.append_user_utterance(session_id, "follow-up")
        assert session_handler.get_history_turn_count(session_id) > 0

        # Second request sends different history — should be ignored.
        second_payload = {
            "history": [
                {"role": "user", "content": "OVERWRITE ATTEMPT"},
                {"role": "assistant", "content": "OVERWRITE ATTEMPT"},
            ]
        }
        rendered_2, info_2 = start_history.resolve_history(session_handler, session_id, second_payload)

        # Guard should return early with no history_info and preserve accumulated history.
        assert info_2 is None
        assert "OVERWRITE ATTEMPT" not in rendered_2
        assert "first hello" in rendered_2
