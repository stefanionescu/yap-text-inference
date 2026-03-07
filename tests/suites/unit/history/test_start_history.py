"""Unit tests for start-message history/token accounting helpers."""

from __future__ import annotations

from src.tokens import count_tokens_chat
from src.state.session import SessionState
import src.messages.start.history as start_history
from src.handlers.session.manager import SessionHandler
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.handlers.session.history.settings import HistoryRuntimeConfig


def _history_config(
    *,
    deploy_chat: bool,
    deploy_tool: bool,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
) -> HistoryRuntimeConfig:
    return HistoryRuntimeConfig(
        deploy_chat=deploy_chat,
        deploy_tool=deploy_tool,
        chat_trigger_tokens=chat_trigger_tokens,
        chat_target_tokens=chat_target_tokens,
        default_tool_history_tokens=None,
    )


def _build_session_handler(
    *,
    deploy_chat: bool = True,
    deploy_tool: bool = False,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
    tool_history_budget: int | None = None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_history_budget=tool_history_budget,
        history_config=_history_config(
            deploy_chat=deploy_chat,
            deploy_tool=deploy_tool,
            chat_trigger_tokens=chat_trigger_tokens,
            chat_target_tokens=chat_target_tokens,
        ),
    )


def _make_state(handler: SessionHandler) -> SessionState:
    state = SessionState(meta={})
    handler.initialize_session(state)
    return state


def _history_turn_count(state: SessionState) -> int:
    if state.history_turns is not None:
        return len(state.history_turns)
    if state.tool_history_turns is not None:
        return len(state.tool_history_turns)
    return 0


def test_resolve_history_renders_turns() -> None:
    with use_local_tokenizers():
        handler = _build_session_handler()
        state = _make_state(handler)
        msg = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "how are you"},
                {"role": "assistant", "content": "great"},
            ]
        }

        turns = start_history.resolve_history(handler, state, msg)

        assert turns[0].user == "hello"
        assert turns[-1].assistant == "great"


def test_resolve_history_trims_when_over_budget() -> None:
    with use_local_tokenizers():
        handler = _build_session_handler(chat_trigger_tokens=6, chat_target_tokens=4)
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

        turns = start_history.resolve_history(handler, state, msg)

        assert state.history_turns is not None
        assert len(state.history_turns) < 3
        assert isinstance(turns, list)


def test_trim_chat_user_utterance_uses_effective_budget() -> None:
    with use_local_tokenizers():
        handler = _build_session_handler()
        state = _make_state(handler)
        state.check_screen_prefix_tokens = 495

        trimmed = start_history.trim_chat_user_utterance(handler, state, "alpha bravo charlie")
        assert count_tokens_chat(trimmed) <= 5


def test_resolve_history_allows_seed_on_fresh_session() -> None:
    """Fresh session with 0 turns accepts client-sent history."""
    with use_local_tokenizers():
        handler = _build_session_handler()
        state = _make_state(handler)

        assert _history_turn_count(state) == 0

        msg = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
        }

        turns = start_history.resolve_history(handler, state, msg)

        assert any(turn.user == "hello" for turn in turns)
        assert _history_turn_count(state) == 1


def test_resolve_history_ignores_history_after_first_request() -> None:
    """Guard: if a session already has turns, client-sent history is ignored."""
    with use_local_tokenizers():
        handler = _build_session_handler()
        state = _make_state(handler)

        seed_msg = {
            "history": [
                {"role": "user", "content": "first hello"},
                {"role": "assistant", "content": "first hi"},
            ]
        }
        turns_1 = start_history.resolve_history(handler, state, seed_msg)
        assert any(turn.user == "first hello" for turn in turns_1)

        handler.append_user_utterance(state, "follow-up")
        assert _history_turn_count(state) > 0

        second_msg = {
            "history": [
                {"role": "user", "content": "OVERWRITE ATTEMPT"},
                {"role": "assistant", "content": "OVERWRITE ATTEMPT"},
            ]
        }
        turns_2 = start_history.resolve_history(handler, state, second_msg)

        assert not any("OVERWRITE ATTEMPT" in turn.user for turn in turns_2)
        assert any(turn.user == "first hello" for turn in turns_2)


def test_resolve_history_tool_only_trims_at_import() -> None:
    """Tool-only mode trims tool_history_turns eagerly at import time."""
    with use_local_tokenizers():
        handler = _build_session_handler(deploy_chat=False, deploy_tool=True, tool_history_budget=10)
        state = SessionState(meta={})
        handler.initialize_session(state)

        messages: list[dict[str, str]] = []
        for i in range(10):
            messages.append({"role": "user", "content": f"word{i} extra{i} more{i}"})

        msg = {"history": messages}
        start_history.resolve_history(handler, state, msg)

        assert state.history_turns is None
        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) < 10
        assert len(state.tool_history_turns) >= 1


def test_resolve_history_tool_only_keeps_single_oversized_seed_turn() -> None:
    """Tool-only seed history keeps a single oversized user turn as-is."""
    with use_local_tokenizers():
        handler = _build_session_handler(deploy_chat=False, deploy_tool=True, tool_history_budget=3)
        state = SessionState(meta={})
        handler.initialize_session(state)

        msg = {
            "history": [
                {"role": "user", "content": "alpha bravo charlie delta echo foxtrot"},
            ]
        }
        start_history.resolve_history(handler, state, msg)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        assert state.tool_history_turns[0].user == "alpha bravo charlie delta echo foxtrot"


def test_resolve_history_both_modes_stores_chat_and_tool_separately() -> None:
    """Both mode keeps assistant turns in chat store and user-only turns in tool store."""
    with use_local_tokenizers():
        handler = _build_session_handler(deploy_chat=True, deploy_tool=True, tool_history_budget=8)
        state = SessionState(meta={})
        handler.initialize_session(state)

        msg = {
            "history": [
                {"role": "user", "content": "hello one"},
                {"role": "assistant", "content": "hi"},
                {"role": "user", "content": "show this please"},
                {"role": "assistant", "content": "ok"},
            ]
        }
        start_history.resolve_history(handler, state, msg)

        assert state.history_turns is not None
        assert state.tool_history_turns is not None
        assert any((turn.assistant or "").strip() for turn in state.history_turns)
        assert all((turn.assistant or "") == "" for turn in state.tool_history_turns)
