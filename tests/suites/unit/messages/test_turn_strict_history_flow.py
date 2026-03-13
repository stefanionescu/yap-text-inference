"""Unit tests for bootstrap-only start flow and committed chat-message planning."""

from __future__ import annotations

import sys
import pytest
import asyncio
import subprocess  # nosec B404
import src.messages.turn as turn_mod
from src.config import DEFAULT_CHECK_SCREEN_PREFIX
from src.handlers.session.manager import SessionHandler
from src.state.session import ChatMessage, SessionState
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.handlers.session.history.settings import HistoryRuntimeConfig
from tests.support.messages.unit import (
    CHAT_MESSAGES,
    HISTORY_PAYLOAD,
    ASSISTANT_FIRST_PAYLOAD,
    ASSISTANT_FIRST_MESSAGES,
)

# This test intentionally spawns the local interpreter to validate a clean-process import path.


class _NoopWS:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, text: str) -> None:
        self.sent.append(text)

    async def close(self, code: int = 1008) -> None:
        _ = code
        self.closed = True


def _build_chat_handler(
    *,
    chat_trigger_tokens: int,
    chat_target_tokens: int,
    tokenizer=None,
) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        chat_tokenizer=tokenizer,
        history_config=HistoryRuntimeConfig(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=chat_trigger_tokens,
            chat_target_tokens=chat_target_tokens,
            default_tool_history_tokens=None,
        ),
    )


def _build_tool_handler(*, tokenizer=None) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        tool_tokenizer=tokenizer,
        history_config=HistoryRuntimeConfig(
            deploy_chat=False,
            deploy_tool=True,
            chat_trigger_tokens=100,
            chat_target_tokens=80,
            default_tool_history_tokens=None,
        ),
    )


def test_bootstrap_start_imports_history_without_spawning_turn_state() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80, tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": HISTORY_PAYLOAD[:2],
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello can you help me plan a trip",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert state.active_request_task is None
        assert state.chat_history_messages == [
            CHAT_MESSAGES[0],
            CHAT_MESSAGES[1],
        ]
        assert ws.sent[-1].startswith('{"type": "done"')


def test_bootstrap_start_imports_assistant_first_history_without_reordering() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_handler(chat_trigger_tokens=200, chat_target_tokens=160, tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": ASSISTANT_FIRST_PAYLOAD[:4],
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello can you help me plan a trip",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert state.active_request_task is None
        assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[:4]
        assert ws.sent[-1].startswith('{"type": "done"')


def test_plan_message_turn_preserves_committed_history_without_provisional_insert() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=4, chat_target_tokens=2)
    state = SessionState(meta={})
    handler.initialize_session(state)

    state.chat_history_messages = [
        ChatMessage(role="user", content="hello can you help me plan a trip"),
        ChatMessage(role="assistant", content="sure tell me your budget"),
    ]

    plan = asyncio.run(
        turn_mod._plan_message_turn(
            _NoopWS(),
            {"user_utterance": "three"},
            state,
            session_handler=handler,
        )
    )

    assert plan is not None
    assert plan.history_turn_id is None
    assert state.chat_history_messages is not None
    assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget"),
    ]
    assert [(msg.role, msg.content) for msg in plan.history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget"),
    ]


def test_plan_message_turn_keeps_full_history_when_prefix_only_input_normalizes_empty() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80)
    state = SessionState(meta={})
    handler.initialize_session(state)
    state.chat_history_messages = [
        ChatMessage(role="user", content="hello can you help me plan a trip"),
        ChatMessage(role="assistant", content="sure tell me your budget"),
    ]

    plan = asyncio.run(
        turn_mod._plan_message_turn(
            _NoopWS(),
            {"user_utterance": DEFAULT_CHECK_SCREEN_PREFIX},
            state,
            session_handler=handler,
        )
    )

    assert plan is not None
    assert plan.history_turn_id is None
    assert state.chat_history_messages is not None
    assert [(msg.role, msg.content) for msg in state.chat_history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget"),
    ]
    assert [(msg.role, msg.content) for msg in plan.history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "sure tell me your budget"),
    ]


def test_plan_message_turn_preserves_assistant_first_committed_history() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=200, chat_target_tokens=160)
    state = SessionState(meta={})
    handler.initialize_session(state)
    state.chat_history_messages = ASSISTANT_FIRST_MESSAGES[:4]

    plan = asyncio.run(
        turn_mod._plan_message_turn(
            _NoopWS(),
            {"user_utterance": "also remind me to pack a rain jacket and travel adapter"},
            state,
            session_handler=handler,
        )
    )

    assert plan is not None
    assert plan.history_turn_id is None
    assert state.chat_history_messages == ASSISTANT_FIRST_MESSAGES[:4]
    assert plan.history_messages == ASSISTANT_FIRST_MESSAGES[:4]


def test_bootstrap_start_imports_tool_history_in_dual_mode_without_execution() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = SessionHandler(
            chat_engine=None,
            tool_history_budget=20,
            chat_tokenizer=tokenizer,
            tool_tokenizer=tokenizer,
            history_config=HistoryRuntimeConfig(
                deploy_chat=True,
                deploy_tool=True,
                chat_trigger_tokens=100,
                chat_target_tokens=80,
                default_tool_history_tokens=20,
            ),
        )
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": HISTORY_PAYLOAD[:2],
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello can you help me plan a trip",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert state.chat_history_messages == [
            CHAT_MESSAGES[0],
            CHAT_MESSAGES[1],
        ]
        assert state.tool_history_turns is not None
        assert [turn.user for turn in state.tool_history_turns] == [CHAT_MESSAGES[0].content]
        assert state.active_request_task is None


@pytest.mark.parametrize(
    ("extra_payload", "expected_fields"),
    [
        ({"gender": "female"}, "gender"),
        ({"personality": "calm"}, "personality"),
        ({"chat_prompt": "hello can you help me plan a trip"}, "chat_prompt"),
        ({"sampling": {}}, "sampling"),
        ({"sampling_params": {"top_p": 0.9}}, "sampling_params"),
        ({"temperature": 0.8, "top_p": 0.9}, "temperature, top_p"),
    ],
)
def test_bootstrap_start_rejects_chat_only_fields_in_tool_only_mode(
    extra_payload: dict[str, object],
    expected_fields: str,
) -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_handler(tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": [{"role": "user", "content": "check the calendar for next tuesday flight times"}],
                    **extra_payload,
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is False
        assert ws.closed is True
        assert any("invalid_settings" in payload for payload in ws.sent)
        assert any(expected_fields in payload for payload in ws.sent)
        assert state.tool_history_turns == []
        assert state.meta["chat_gender"] is None
        assert state.meta["chat_personality"] is None
        assert state.meta["chat_prompt"] is None


def test_bootstrap_start_accepts_tool_only_start_without_chat_fields() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_tool_handler(tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": [{"role": "user", "content": "check the calendar for next tuesday flight times"}],
                    "check_screen_prefix": "CHECK NOW:",
                    "screen_checked_prefix": "ALREADY CHECKED:",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert ws.sent[-1].startswith('{"type": "done"')
        assert state.tool_history_turns is not None
        assert [turn.user for turn in state.tool_history_turns] == ["check the calendar for next tuesday flight times"]
        assert state.meta["chat_gender"] is None
        assert state.meta["chat_personality"] is None
        assert state.meta["chat_prompt"] is None


def test_bootstrap_start_rejects_seed_history_that_cannot_fit_latest_turn() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_handler(chat_trigger_tokens=200, chat_target_tokens=120, tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()
        oversized_history = [{"role": "user", "content": " ".join(["hello"] * 7000)}]

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": oversized_history,
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello can you help me plan a trip",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is False
        assert ws.closed is True
        assert any("text_too_long" in payload for payload in ws.sent)


def test_messages_turn_imports_without_circular_dependency() -> None:
    proc = subprocess.run(  # noqa: S603  # nosec B603
        [sys.executable, "-c", "import src.messages.turn"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
