"""Unit tests for chat stream history commit behavior."""

from __future__ import annotations

import asyncio
from fastapi import WebSocketDisconnect
from src.state.session import SessionState
from src.config import DEFAULT_CHECK_SCREEN_PREFIX
from src.handlers.session.manager import SessionHandler
from src.handlers.websocket.helpers import stream_chat_response
from src.handlers.session.history.settings import HistoryRuntimeConfig


class _NoopWS:
    async def send_text(self, _text: str) -> None:
        return None


class _DisconnectAfterSecondSendWS:
    def __init__(self) -> None:
        self._send_count = 0

    async def send_text(self, _text: str) -> None:
        self._send_count += 1
        if self._send_count >= 2:
            raise WebSocketDisconnect()


def _build_handler() -> SessionHandler:
    return SessionHandler(
        chat_engine=None,
        history_config=HistoryRuntimeConfig(
            deploy_chat=True,
            deploy_tool=False,
            chat_trigger_tokens=1000,
            chat_target_tokens=800,
            default_tool_history_tokens=None,
        ),
    )


async def _empty_stream():
    if False:
        yield ""


async def _error_stream():
    raise RuntimeError("boom")
    yield ""


async def _two_chunk_stream():
    yield "alpha"
    yield "beta"


def test_stream_chat_response_skips_history_for_empty_output_without_provisional_turn() -> None:
    handler = _build_handler()
    state = SessionState(meta={})
    handler.initialize_session(state)

    out = asyncio.run(
        stream_chat_response(
            _NoopWS(),
            _empty_stream(),
            state,
            "hello can you help me plan a trip",
            history_user_utt="hello can you help me plan a trip",
            session_handler=handler,
        )
    )

    assert out == ""
    assert state.chat_history_messages == []


def test_stream_chat_response_skips_history_for_error_before_visible_text() -> None:
    handler = _build_handler()
    state = SessionState(meta={})
    handler.initialize_session(state)

    try:
        asyncio.run(
            stream_chat_response(
                _NoopWS(),
                _error_stream(),
                state,
                "hello can you help me plan a trip",
                history_user_utt="hello can you help me plan a trip",
                session_handler=handler,
            )
        )
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("expected RuntimeError")

    assert state.chat_history_messages == []


def test_stream_chat_response_commits_partial_history_after_disconnect_with_visible_text() -> None:
    handler = _build_handler()
    state = SessionState(meta={})
    handler.initialize_session(state)

    out = asyncio.run(
        stream_chat_response(
            _DisconnectAfterSecondSendWS(),
            _two_chunk_stream(),
            state,
            "hello can you help me plan a trip",
            history_user_utt="hello can you help me plan a trip",
            session_handler=handler,
        )
    )

    assert out == "alpha"
    assert state.chat_history_messages is not None
    assert [(message.role, message.content) for message in state.chat_history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "alpha"),
    ]


def test_stream_chat_response_skips_commit_when_history_user_is_empty() -> None:
    handler = _build_handler()
    state = SessionState(meta={})
    handler.initialize_session(state)

    out = asyncio.run(
        stream_chat_response(
            _NoopWS(),
            _two_chunk_stream(),
            state,
            "",
            history_user_utt="",
            session_handler=handler,
        )
    )

    assert out == "alphabeta"
    assert state.chat_history_messages == []


def test_stream_chat_response_does_not_persist_internal_screen_prefixes() -> None:
    handler = _build_handler()
    state = SessionState(meta={})
    handler.initialize_session(state)

    out = asyncio.run(
        stream_chat_response(
            _NoopWS(),
            _two_chunk_stream(),
            state,
            f"{DEFAULT_CHECK_SCREEN_PREFIX} hello",
            history_user_utt=f"{DEFAULT_CHECK_SCREEN_PREFIX} hello can you help me plan a trip",
            session_handler=handler,
        )
    )

    assert out == "alphabeta"
    assert state.chat_history_messages is not None
    assert [(message.role, message.content) for message in state.chat_history_messages] == [
        ("user", "hello can you help me plan a trip"),
        ("assistant", "alphabeta"),
    ]
