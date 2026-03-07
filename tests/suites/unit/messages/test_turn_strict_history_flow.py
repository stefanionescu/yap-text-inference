"""Unit tests for strict chat planning flow (post-trim history + latest separately)."""

from __future__ import annotations

import sys
import copy
import asyncio
import subprocess
import src.messages.turn as turn_mod
from src.state.session import SessionState
from src.config import DEFAULT_CHECK_SCREEN_PREFIX
from src.handlers.session.manager import SessionHandler
from src.handlers.session.history.settings import HistoryRuntimeConfig


class _NoopWS:
    async def send_text(self, _text: str) -> None:
        pass

    async def close(self, code: int = 1008) -> None:
        _ = code
        pass


def _build_chat_handler(*, chat_trigger_tokens: int, chat_target_tokens: int) -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        history_config=HistoryRuntimeConfig(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=chat_trigger_tokens,
            chat_target_tokens=chat_target_tokens,
            default_tool_history_tokens=None,
        ),
    )


def test_build_start_turn_plan_excludes_latest_from_planned_history() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80)
    state = SessionState(meta={})
    handler.initialize_session(state)

    msg = {
        "history": [
            {"role": "user", "content": "seed user"},
            {"role": "assistant", "content": "seed assistant"},
        ],
        "user_utterance": "latest user",
    }
    plan = turn_mod._build_start_turn_plan(
        state,
        msg,
        copy.deepcopy(state.meta),
        session_handler=handler,
        sampling_overrides={},
    )

    assert plan.history_turn_id is not None
    assert state.history_turns is not None
    assert any(turn.turn_id == plan.history_turn_id for turn in state.history_turns)
    assert all(turn.turn_id != plan.history_turn_id for turn in plan.history_turns)
    assert [turn.turn_id for turn in plan.history_turns] == [
        turn.turn_id for turn in state.history_turns if turn.turn_id != plan.history_turn_id
    ]


def test_plan_message_turn_uses_post_trim_history_without_latest() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=4, chat_target_tokens=2)
    state = SessionState(meta={})
    handler.initialize_session(state)

    handler.append_user_utterance(state, "one")
    handler.append_user_utterance(state, "two")
    assert state.history_turns is not None
    assert len(state.history_turns) == 2

    plan = asyncio.run(
        turn_mod._plan_message_turn(
            _NoopWS(),
            {"user_utterance": "three"},
            state,
            session_handler=handler,
        )
    )

    assert plan is not None
    assert plan.history_turn_id is not None
    assert state.history_turns is not None
    assert len(state.history_turns) == 1
    assert state.history_turns[0].turn_id == plan.history_turn_id
    assert plan.history_turns == []


def test_build_start_turn_plan_keeps_full_history_when_no_chat_turn_appended() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80)
    state = SessionState(meta={})
    handler.initialize_session(state)

    msg = {
        "history": [
            {"role": "user", "content": "seed user"},
            {"role": "assistant", "content": "seed assistant"},
            {"role": "user", "content": "seed user 2"},
            {"role": "assistant", "content": "seed assistant 2"},
        ],
        "user_utterance": "",
    }
    plan = turn_mod._build_start_turn_plan(
        state,
        msg,
        copy.deepcopy(state.meta),
        session_handler=handler,
        sampling_overrides={},
    )

    assert plan.history_turn_id is None
    assert state.history_turns is not None
    assert [turn.turn_id for turn in plan.history_turns] == [turn.turn_id for turn in state.history_turns]


def test_plan_message_turn_keeps_full_history_when_no_chat_turn_appended() -> None:
    handler = _build_chat_handler(chat_trigger_tokens=100, chat_target_tokens=80)
    state = SessionState(meta={})
    handler.initialize_session(state)
    handler.append_user_utterance(state, "one")
    handler.append_user_utterance(state, "two")
    assert state.history_turns is not None
    before_ids = [turn.turn_id for turn in state.history_turns]

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
    assert state.history_turns is not None
    assert [turn.turn_id for turn in state.history_turns] == before_ids
    assert [turn.turn_id for turn in plan.history_turns] == before_ids


def test_messages_turn_imports_without_circular_dependency() -> None:
    proc = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import src.messages.turn"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
