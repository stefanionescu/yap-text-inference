"""Unit tests for session task supervision."""

from __future__ import annotations

import json
import asyncio
from src.state.session import SessionState
from src.config.websocket import WS_ERROR_INTERNAL
from src.handlers.session.manager import SessionHandler
from src.handlers.websocket.supervision import spawn_session_task


class _NoopWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, text: str) -> None:
        self.sent.append(text)


async def _success_operation() -> None:
    await asyncio.sleep(0)


async def _failing_operation() -> None:
    raise RuntimeError("boom")


async def _disconnect_operation() -> None:
    raise RuntimeError("websocket is not connected")


def _make_handler() -> SessionHandler:
    return SessionHandler(chat_engine=None)


def test_spawn_session_task_cleans_up_after_success() -> None:
    async def scenario() -> None:
        ws = _NoopWS()
        state = SessionState(meta={})
        handler = _make_handler()

        task = await spawn_session_task(
            ws,
            state,
            request_id="req-success",
            operation=_success_operation(),
            session_handler=handler,
        )

        assert task is not None
        await task
        assert state.active_request_id is None
        assert state.active_request_task is None
        assert ws.sent == []

    asyncio.run(scenario())


def test_spawn_session_task_sends_internal_error_on_failure() -> None:
    async def scenario() -> None:
        ws = _NoopWS()
        state = SessionState(meta={})
        handler = _make_handler()

        task = await spawn_session_task(
            ws,
            state,
            request_id="req-fail",
            operation=_failing_operation(),
            session_handler=handler,
        )

        assert task is not None
        await task
        assert state.active_request_id is None
        assert state.active_request_task is None
        assert len(ws.sent) == 1
        payload = json.loads(ws.sent[0])
        assert payload["type"] == "error"
        assert payload["code"] == WS_ERROR_INTERNAL

    asyncio.run(scenario())


def test_spawn_session_task_swallows_expected_disconnect_errors() -> None:
    async def scenario() -> None:
        ws = _NoopWS()
        state = SessionState(meta={})
        handler = _make_handler()

        task = await spawn_session_task(
            ws,
            state,
            request_id="req-disconnect",
            operation=_disconnect_operation(),
            session_handler=handler,
        )

        assert task is not None
        await task
        assert state.active_request_id is None
        assert state.active_request_task is None
        assert ws.sent == []

    asyncio.run(scenario())
