"""Unit tests for screen follow-up prefix behavior."""

from __future__ import annotations

from src.state.session import SessionState
import src.messages.start.history as start_history
from src.handlers.session.manager import SessionHandler


def test_trim_user_utterance_for_followup_uses_followup_budget(monkeypatch) -> None:
    handler = SessionHandler(chat_engine=None)
    state = SessionState(meta={})
    handler.initialize_session(state)

    captured: dict[str, bool] = {}

    def _budget_stub(_state, *, for_followup=False):
        captured["for_followup"] = for_followup
        return 64

    monkeypatch.setattr(handler, "get_effective_user_utt_max_tokens", _budget_stub)
    monkeypatch.setattr(start_history, "DEPLOY_CHAT", True)
    monkeypatch.setattr(start_history, "DEPLOY_TOOL", False)
    trimmed = start_history.trim_user_utterance(handler, state, "hello there", for_followup=True)
    assert trimmed
    assert captured.get("for_followup") is True


def test_session_handler_tracks_screen_followup_pending_state() -> None:
    handler = SessionHandler(chat_engine=None)
    state = SessionState(meta={})
    handler.initialize_session(state)
    assert handler.has_screen_followup_pending(state) is False
    handler.set_screen_followup_pending(state, True)
    assert handler.has_screen_followup_pending(state) is True
    handler.set_screen_followup_pending(state, False)
    assert handler.has_screen_followup_pending(state) is False
