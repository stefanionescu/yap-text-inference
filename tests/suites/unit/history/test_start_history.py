"""Unit tests for start-message history and user-normalization helpers."""

from __future__ import annotations

from src.config import DEFAULT_CHECK_SCREEN_PREFIX
from src.handlers.session.manager import SessionHandler
from src.state.session import ChatMessage, SessionState
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.handlers.session.history.settings import HistoryRuntimeConfig
from src.messages.history import resolve_history, resolve_user_utterances
from tests.support.messages.unit import (
    CHAT_MESSAGES,
    HISTORY_PAYLOAD,
    ASSISTANT_FIRST_PAYLOAD,
    ASSISTANT_FIRST_MESSAGES,
    tool_turn_payloads,
)


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
    tokenizer=None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_history_budget=tool_history_budget,
        chat_tokenizer=tokenizer,
        tool_tokenizer=tokenizer,
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
    if state.chat_history_messages is not None:
        return len(state.chat_history_messages)
    if state.tool_history_turns is not None:
        return len(state.tool_history_turns)
    return 0


def test_resolve_history_renders_messages() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)
        msg = {"history": HISTORY_PAYLOAD[:4]}

        messages = resolve_history(handler, state, msg)

        assert [(message.role, message.content) for message in messages] == [
            (CHAT_MESSAGES[0].role, CHAT_MESSAGES[0].content),
            (CHAT_MESSAGES[1].role, CHAT_MESSAGES[1].content),
            (CHAT_MESSAGES[2].role, CHAT_MESSAGES[2].content),
            (CHAT_MESSAGES[3].role, CHAT_MESSAGES[3].content),
        ]


def test_resolve_history_trims_when_over_budget() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(chat_trigger_tokens=6, chat_target_tokens=4, tokenizer=tokenizer)
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

        messages = resolve_history(handler, state, msg)

        assert state.chat_history_messages is not None
        assert len(state.chat_history_messages) < 6
        assert isinstance(messages, list)


def test_resolve_user_utterances_normalizes_without_chat_trimming() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)
        state.check_screen_prefix_tokens = 495

        chat_user, tool_user = resolve_user_utterances(
            handler,
            state,
            f"{DEFAULT_CHECK_SCREEN_PREFIX} alpha bravo charlie",
        )
        assert chat_user == "alpha bravo charlie"
        assert tool_user == "alpha bravo charlie"


def test_resolve_history_allows_seed_on_fresh_session() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        assert _history_turn_count(state) == 0

        msg = {
            "history": [
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "hi there"},
            ]
        }

        messages = resolve_history(handler, state, msg)

        assert any(message.content == "hello" for message in messages)
        assert _history_turn_count(state) == 2


def test_resolve_history_preserves_assistant_first_seed_on_fresh_session() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        messages = resolve_history(handler, state, {"history": ASSISTANT_FIRST_PAYLOAD[:4]})

        assert messages == ASSISTANT_FIRST_MESSAGES[:4]
        assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[:4]
        assert _history_turn_count(state) == 4


def test_resolve_history_ignores_history_after_first_request() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        seed_msg = {
            "history": [
                {"role": "user", "content": "first hello"},
                {"role": "assistant", "content": "first hi"},
            ]
        }
        messages_1 = resolve_history(handler, state, seed_msg)
        assert any(message.content == "first hello" for message in messages_1)

        handler.append_chat_turn(state, "follow-up", "")
        assert _history_turn_count(state) > 0

        second_msg = {
            "history": [
                {"role": "user", "content": "OVERWRITE ATTEMPT"},
                {"role": "assistant", "content": "OVERWRITE ATTEMPT"},
            ]
        }
        messages_2 = resolve_history(handler, state, second_msg)

        assert not any("OVERWRITE ATTEMPT" in message.content for message in messages_2)
        assert any(message.content == "first hello" for message in messages_2)


def test_resolve_history_tool_only_trims_at_import() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(
            deploy_chat=False,
            deploy_tool=True,
            tool_history_budget=10,
            tokenizer=tokenizer,
        )
        state = SessionState(meta={})
        handler.initialize_session(state)

        msg = {"history": tool_turn_payloads() * 3}
        resolve_history(handler, state, msg)

        assert state.chat_history_messages is None
        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) < 10
        assert len(state.tool_history_turns) >= 1


def test_resolve_history_tool_only_crops_single_oversized_seed_turn() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(
            deploy_chat=False,
            deploy_tool=True,
            tool_history_budget=3,
            tokenizer=tokenizer,
        )
        state = SessionState(meta={})
        handler.initialize_session(state)

        msg = {
            "history": [
                {"role": "user", "content": "check the calendar for next tuesday flight times"},
            ]
        }
        resolve_history(handler, state, msg)

        assert state.tool_history_turns is not None
        assert len(state.tool_history_turns) == 1
        assert state.tool_history_turns[0].user == "tuesday flight times"
        assert handler._history.get_tool_history_text(state, max_tokens=3) == "tuesday flight times"


def test_resolve_history_trims_assistant_first_seed_by_whole_groups() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(chat_trigger_tokens=60, chat_target_tokens=40, tokenizer=tokenizer)
        state = _make_state(handler)

        messages = resolve_history(handler, state, {"history": ASSISTANT_FIRST_PAYLOAD})

        assert messages == ASSISTANT_FIRST_MESSAGES[-2:]
        assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[-2:]


def test_resolve_history_both_modes_stores_chat_and_tool_separately() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(deploy_chat=True, deploy_tool=True, tool_history_budget=8, tokenizer=tokenizer)
        state = SessionState(meta={})
        handler.initialize_session(state)

        msg = {
            "history": [
                {"role": "user", "content": "hello one"},
                {"role": "assistant", "content": "hi"},
                {"role": "assistant", "content": "more"},
                {"role": "user", "content": "show this please"},
            ]
        }
        resolve_history(handler, state, msg)

        assert state.chat_history_messages is not None
        assert state.tool_history_turns is not None
        assert [(message.role, message.content) for message in state.chat_history_messages] == [
            ("user", "hello one"),
            ("assistant", "hi"),
            ("assistant", "more"),
            ("user", "show this please"),
        ]
        assert [turn.user for turn in state.tool_history_turns] == ["hello one", "show this please"]


def test_resolve_history_both_modes_preserves_assistant_first_chat_and_user_only_tool_history() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(
            deploy_chat=True, deploy_tool=True, tool_history_budget=20, tokenizer=tokenizer
        )
        state = SessionState(meta={})
        handler.initialize_session(state)

        resolve_history(handler, state, {"history": ASSISTANT_FIRST_PAYLOAD[:4]})

        assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[:4]
        assert state.tool_history_turns is not None
        assert [turn.user for turn in state.tool_history_turns] == [
            ASSISTANT_FIRST_MESSAGES[2].content,
        ]


def test_resolve_history_merges_consecutive_users_on_import() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_session_handler(tokenizer=tokenizer)
        state = _make_state(handler)

        msg = {
            "history": [
                {"role": "user", "content": "one"},
                {"role": "user", "content": "two"},
                {"role": "assistant", "content": "reply"},
            ]
        }

        messages = resolve_history(handler, state, msg)

        assert messages == [
            ChatMessage(role="user", content="one\n\ntwo"),
            ChatMessage(role="assistant", content="reply"),
        ]
