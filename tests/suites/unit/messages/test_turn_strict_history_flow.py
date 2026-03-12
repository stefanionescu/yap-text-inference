"""Unit tests for bootstrap-only start flow and committed chat-message planning."""

from __future__ import annotations

import sys
import asyncio
import subprocess
import src.messages.turn as turn_mod
from src.config import DEFAULT_CHECK_SCREEN_PREFIX
from src.handlers.session.manager import SessionHandler
from src.state.session import ChatMessage, SessionState
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.handlers.session.history.settings import HistoryRuntimeConfig


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


def test_bootstrap_start_imports_history_without_spawning_turn_state() -> None:
    with use_local_tokenizers() as tokenizer:
        handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80, tokenizer=tokenizer)
        state = SessionState(meta={})
        ws = _NoopWS()

        ok = asyncio.run(
            turn_mod._bootstrap_start_turn(
                ws,
                {
                    "history": [
                        {"role": "user", "content": "seed user"},
                        {"role": "assistant", "content": "seed assistant"},
                    ],
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert state.active_request_task is None
        assert state.chat_history_messages == [
            ChatMessage(role="user", content="seed user"),
            ChatMessage(role="assistant", content="seed assistant"),
        ]
        assert ws.sent[-1].startswith('{"type": "done"')


def test_plan_message_turn_preserves_committed_history_without_provisional_insert() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=4, chat_target_tokens=2)
    state = SessionState(meta={})
    handler.initialize_session(state)

    state.chat_history_messages = [
        ChatMessage(role="user", content="one"),
        ChatMessage(role="assistant", content="reply one"),
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
        ("user", "one"),
        ("assistant", "reply one"),
    ]
    assert [(msg.role, msg.content) for msg in plan.history_messages] == [
        ("user", "one"),
        ("assistant", "reply one"),
    ]


def test_plan_message_turn_keeps_full_history_when_prefix_only_input_normalizes_empty() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80)
    state = SessionState(meta={})
    handler.initialize_session(state)
    state.chat_history_messages = [
        ChatMessage(role="user", content="one"),
        ChatMessage(role="assistant", content="reply"),
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
        ("user", "one"),
        ("assistant", "reply"),
    ]
    assert [(msg.role, msg.content) for msg in plan.history_messages] == [
        ("user", "one"),
        ("assistant", "reply"),
    ]


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
                    "history": [
                        {"role": "user", "content": "seed user"},
                        {"role": "assistant", "content": "seed assistant"},
                    ],
                    "gender": "female",
                    "personality": "calm",
                    "chat_prompt": "hello",
                },
                state,
                session_handler=handler,
            )
        )

        assert ok is True
        assert state.chat_history_messages == [
            ChatMessage(role="user", content="seed user"),
            ChatMessage(role="assistant", content="seed assistant"),
        ]
        assert state.tool_history_turns is not None
        assert [turn.user for turn in state.tool_history_turns] == ["seed user"]
        assert state.active_request_task is None


def test_messages_turn_imports_without_circular_dependency() -> None:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import src.messages.turn"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
