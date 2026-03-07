"""Unit tests for screen follow-up prefix behavior."""

from __future__ import annotations

from src.state.session import SessionState
import src.messages.start.history as start_history
from src.handlers.session.manager import SessionHandler
from src.handlers.session.history.settings import HistoryRuntimeConfig


def test_trim_chat_user_utterance_for_followup_uses_followup_budget(monkeypatch) -> None:
    handler = SessionHandler(
        chat_engine=None,
        history_config=HistoryRuntimeConfig(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
            default_tool_history_tokens=None,
        ),
    )
    state = SessionState(meta={})
    handler.initialize_session(state)

    captured: dict[str, bool] = {}

    def _budget_stub(_state, *, for_followup=False):
        captured["for_followup"] = for_followup
        return 64

    monkeypatch.setattr(handler, "get_effective_chat_user_utt_max_tokens", _budget_stub)
    trimmed = start_history.trim_chat_user_utterance(handler, state, "hello there", for_followup=True)
    assert trimmed
    assert captured.get("for_followup") is True


def test_session_handler_tracks_screen_followup_pending_state() -> None:
    handler = SessionHandler(
        chat_engine=None,
        history_config=HistoryRuntimeConfig(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
            default_tool_history_tokens=None,
        ),
    )
    state = SessionState(meta={})
    handler.initialize_session(state)
    assert state.screen_followup_pending is False
    handler.set_screen_followup_pending(state, True)
    assert state.screen_followup_pending is True
    handler.set_screen_followup_pending(state, False)
    assert state.screen_followup_pending is False
