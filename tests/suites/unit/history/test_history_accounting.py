"""Unit tests for session history update/accounting behavior."""

from __future__ import annotations

from typing import Any, cast
from src.tokens import count_tokens_tool
import src.handlers.session.history.ops as history_ops
from src.handlers.session.manager import SessionHandler
from src.state.session import HistoryTurn, SessionState
from tests.support.helpers.tokenizer import use_local_tokenizers
import src.handlers.session.history.token_counting as history_tokens
from src.handlers.session.history.settings import HistoryRuntimeConfig


def _history_config(
    *,
    deploy_chat: bool,
    deploy_tool: bool,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
    default_tool_history_tokens: int | None = None,
) -> HistoryRuntimeConfig:
    return HistoryRuntimeConfig(
        deploy_chat=deploy_chat,
        deploy_tool=deploy_tool,
        chat_trigger_tokens=chat_trigger_tokens,
        chat_target_tokens=chat_target_tokens,
        default_tool_history_tokens=default_tool_history_tokens,
    )


def _build_session_handler() -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        history_config=_history_config(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
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


def test_append_history_turn_updates_existing_turn_when_turn_id_provided() -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler()
        state = _make_state(session_handler)

        turn_id = session_handler.append_user_utterance(state, "hello")
        assert turn_id is not None
        assert _history_turn_count(state) == 1

        session_handler.append_history_turn(state, "ignored", "world", turn_id=turn_id)
        rendered = session_handler._history.get_text(state)

        assert _history_turn_count(state) == 1
        assert "User: hello" in rendered
        assert "Assistant: world" in rendered


def test_set_history_turns_keeps_expected_turn_count() -> None:
    with use_local_tokenizers():
        session_handler = _build_session_handler()
        state = _make_state(session_handler)

        turns = [
            HistoryTurn(turn_id="t1", user="u1", assistant="a1"),
            HistoryTurn(turn_id="t2", user="u2", assistant="a2"),
        ]

        rendered = session_handler._history.set_mode_turns(state, chat_turns=turns)

        assert "User: u1" in rendered
        assert "Assistant: a2" in rendered
        assert _history_turn_count(state) == 2


def test_render_tool_history_text_keeps_latest_line_when_single_line_exceeds_budget() -> None:
    with use_local_tokenizers():
        config = _history_config(deploy_chat=False, deploy_tool=True)
        turns = [HistoryTurn(turn_id="t1", user="one two three four five", assistant="")]
        rendered = history_ops.render_tool_history_text(turns, config=config, max_tokens=3)
        assert rendered == "one two three four five"
        assert count_tokens_tool(rendered) > 3


def test_render_tool_history_text_uses_raw_user_lines() -> None:
    with use_local_tokenizers():
        config = _history_config(deploy_chat=False, deploy_tool=True)
        turns = [
            HistoryTurn(turn_id="t1", user="first line", assistant="assistant one"),
            HistoryTurn(turn_id="t2", user="second line", assistant="assistant two"),
        ]
        rendered = history_ops.render_tool_history_text(turns, config=config, max_tokens=20)
        assert rendered == "first line\nsecond line"
        assert "User:" not in rendered
        assert "Assistant:" not in rendered


def _build_tool_only_handler(tool_budget: int = 10) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_history_budget=tool_budget,
        history_config=_history_config(
            deploy_chat=False,
            deploy_tool=True,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
        ),
    )


def _build_chat_only_handler(
    *,
    chat_trigger_tokens: int = 1000,
    chat_target_tokens: int = 800,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        history_config=_history_config(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=chat_trigger_tokens,
            chat_target_tokens=chat_target_tokens,
        ),
    )


def test_tool_only_mode_keeps_chat_history_inactive() -> None:
    with use_local_tokenizers():
        handler = _build_tool_only_handler(tool_budget=20)
        state = SessionState(meta={})
        handler.initialize_session(state)

        assert state.history_turns is None
        assert state.tool_history_turns == []

        turn_id = handler.append_user_utterance(state, "show me this")
        assert turn_id is not None
        assert state.history_turns is None
        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        assert _history_turn_count(state) == 1


def test_chat_only_mode_keeps_tool_history_inactive() -> None:
    with use_local_tokenizers():
        handler = _build_chat_only_handler()
        state = SessionState(meta={})
        handler.initialize_session(state)

        assert state.history_turns == []
        assert state.tool_history_turns is None

        turn_id = handler.append_user_utterance(state, "hello")
        assert turn_id is not None
        assert state.history_turns is not None
        assert len(state.history_turns) == 1
        assert state.tool_history_turns is None
        assert _history_turn_count(state) == 1


def test_trim_history_tool_only_drops_old_turns() -> None:
    """Tool-only trim_tool_history drops oldest turns to stay within budget."""
    with use_local_tokenizers():
        _build_tool_only_handler(tool_budget=10)
        state = SessionState(meta={})

        turns = [HistoryTurn(turn_id=f"t{i}", user=f"word{i} extra{i} more{i}", assistant="") for i in range(5)]
        state.tool_history_turns = turns
        history_ops.trim_tool_history(state, 6)

        assert len(state.tool_history_turns) < 5
        assert state.tool_history_turns[-1].turn_id == "t4"


def test_trim_history_tool_only_keeps_single_oversized_last_turn() -> None:
    """Tool-only trim_tool_history keeps a single oversized turn as-is."""
    with use_local_tokenizers():
        _build_tool_only_handler(tool_budget=5)
        state = SessionState(meta={})

        long_text = "alpha bravo charlie delta echo foxtrot golf hotel india"
        state.tool_history_turns = [HistoryTurn(turn_id="t1", user=long_text, assistant="")]
        history_ops.trim_tool_history(state, 3)

        assert len(state.tool_history_turns) == 1
        assert state.tool_history_turns[0].user == long_text


def test_trim_history_tool_only_noop_when_under_budget() -> None:
    """Tool-only trim_tool_history is a no-op when under budget."""
    with use_local_tokenizers():
        _build_tool_only_handler(tool_budget=100)
        state = SessionState(meta={})

        turns = [
            HistoryTurn(turn_id="t1", user="hi", assistant=""),
            HistoryTurn(turn_id="t2", user="hello", assistant=""),
        ]
        state.tool_history_turns = turns
        history_ops.trim_tool_history(state, 100)

        assert len(state.tool_history_turns) == 2


def test_append_user_utterance_tool_only_trims_eagerly() -> None:
    """Appending user turns eagerly keeps tool history within budget."""
    with use_local_tokenizers():
        handler = _build_tool_only_handler(tool_budget=6)
        state = SessionState(meta={})
        handler.initialize_session(state)

        for i in range(6):
            handler.append_user_utterance(state, f"word{i} extra{i} more{i}")

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) < 6
        rendered = handler._history.get_tool_history_text(state)
        assert count_tokens_tool(rendered) <= 6


def test_append_user_utterance_chat_only_trims_eagerly() -> None:
    """Appending user turns eagerly keeps chat history under chat thresholds."""
    with use_local_tokenizers():
        handler = _build_chat_only_handler(chat_trigger_tokens=10, chat_target_tokens=6)
        state = SessionState(meta={})
        handler.initialize_session(state)

        for i in range(8):
            handler.append_user_utterance(state, f"turn{i} extra{i}")

        assert state.history_turns is not None
        assert len(state.history_turns) < 8


def test_get_tool_history_text_excludes_latest_without_mutating_store() -> None:
    """include_latest=False returns prior context only and leaves store untouched."""
    with use_local_tokenizers():
        handler = _build_tool_only_handler(tool_budget=30)
        state = SessionState(meta={})
        handler.initialize_session(state)

        handler.append_user_utterance(state, "alpha one")
        handler.append_user_utterance(state, "bravo two")
        handler.append_user_utterance(state, "charlie three")

        with_latest = handler._history.get_tool_history_text(state)
        without_latest = handler._history.get_tool_history_text(state, include_latest=False)

        assert with_latest.endswith("charlie three")
        assert without_latest == "alpha one\nbravo two"
        assert handler._history.get_tool_history_text(state) == with_latest


def test_append_user_utterance_tool_only_keeps_single_oversized_turn() -> None:
    """A single oversized user turn is retained whole during eager append-time trim."""
    with use_local_tokenizers():
        handler = _build_tool_only_handler(tool_budget=3)
        state = SessionState(meta={})
        handler.initialize_session(state)

        long_text = "alpha bravo charlie delta echo foxtrot"
        handler.append_user_utterance(state, long_text)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        kept = state.tool_history_turns[0].user
        assert kept == long_text
        assert handler._history.get_tool_history_text(state) == long_text


class _SpecialAwareTokenizer:
    def count(self, text: str, *, add_special_tokens: bool = False) -> int:
        if not text.strip():
            return 0
        total = len(text.split())
        if add_special_tokens:
            total += 2
        return total

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        tokens = text.split()
        if max_tokens <= 0:
            return ""
        if len(tokens) <= max_tokens:
            return text
        kept = tokens[:max_tokens] if keep == "start" else tokens[-max_tokens:]
        return " ".join(kept)

    def encode_ids(self, text: str) -> list[int]:
        return list(range(len(text.split())))


def test_build_tool_history_accounts_for_special_tokens() -> None:
    tokenizer = cast(Any, _SpecialAwareTokenizer())

    kept = history_tokens.build_tool_history(
        ["one two", "three four"],
        budget=5,
        tool_tokenizer=tokenizer,
    )
    assert kept == "three four"


def test_build_tool_history_keeps_single_oversized_line_with_special_tokens() -> None:
    tokenizer = cast(Any, _SpecialAwareTokenizer())

    kept = history_tokens.build_tool_history(
        ["one two"],
        budget=3,
        tool_tokenizer=tokenizer,
    )
    assert kept == "one two"
