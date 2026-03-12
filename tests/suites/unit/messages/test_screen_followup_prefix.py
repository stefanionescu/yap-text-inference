"""Unit tests for screen follow-up prefix behavior."""

from __future__ import annotations

from src.state.session import SessionState
import src.messages.start.history as start_history
from src.config import DEFAULT_SCREEN_CHECKED_PREFIX
from src.handlers.session.manager import SessionHandler
from src.handlers.session.history.settings import HistoryRuntimeConfig


def test_resolve_user_utterances_strips_followup_prefix_without_trimming() -> None:
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

    chat_user, tool_user = start_history.resolve_user_utterances(
        handler,
        state,
        f"{DEFAULT_SCREEN_CHECKED_PREFIX} hello there",
        for_followup=True,
    )
    assert chat_user == "hello there"
    assert tool_user == "hello there"


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
