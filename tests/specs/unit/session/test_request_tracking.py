"""Unit tests for session request tracking utilities."""

from __future__ import annotations
import asyncio
from src.state.session import SessionState
from src.handlers.session.manager import SessionHandler
from src.handlers.session.requests import (
    is_request_cancelled,
    cancel_session_requests,
    cleanup_session_requests,
)


def _make_state(**kwargs: object) -> SessionState:
    defaults: dict[str, object] = {"meta": {}}
    defaults.update(kwargs)
    return SessionState(**defaults)  # type: ignore[arg-type]


class _FakeTask:
    def __init__(self, *, done: bool = False) -> None:
        self._done = done
        self.cancel_called = False

    def done(self) -> bool:
        return self._done

    def cancel(self) -> None:
        self.cancel_called = True
        self._done = True


# --- is_request_cancelled ---


def test_is_request_cancelled_none_state() -> None:
    assert is_request_cancelled(None, "req1") is True


def test_is_request_cancelled_when_cancel_requested() -> None:
    state = _make_state(active_request_id="req1", cancel_requested=True)
    assert is_request_cancelled(state, "req1") is True


def test_is_request_cancelled_no_active() -> None:
    state = _make_state(active_request_id=None)
    assert is_request_cancelled(state, "req1") is False


def test_is_request_cancelled_matching() -> None:
    state = _make_state(active_request_id="req1")
    assert is_request_cancelled(state, "req1") is False


def test_is_request_cancelled_different() -> None:
    state = _make_state(active_request_id="req2")
    assert is_request_cancelled(state, "req1") is True


# --- cleanup_session_requests ---


def test_cleanup_none_state() -> None:
    result = cleanup_session_requests(None)
    assert result == {"active": ""}


def test_cleanup_extracts_and_clears() -> None:
    state = _make_state(active_request_id="a1")
    result = cleanup_session_requests(state)
    assert result == {"active": "a1"}
    assert state.active_request_id is None


def test_cleanup_clears_task_pointer() -> None:
    task = _FakeTask()
    state = _make_state(active_request_id="a1", active_request_task=task)
    result = cleanup_session_requests(state)
    assert result == {"active": "a1"}
    assert state.active_request_task is None


# --- cancel_session_requests ---


def test_cancel_marks_cancel_requested() -> None:
    state = _make_state(active_request_id="r1")
    cancel_session_requests(state)
    assert state.cancel_requested is True


def test_cancel_cancels_running_task() -> None:
    task = _FakeTask()
    state = _make_state(active_request_task=task)
    cancel_session_requests(state)
    assert task.cancel_called is True


class _DummyEngine:
    def __init__(self) -> None:
        self.aborted: list[str] = []

    async def abort(self, request_id: str) -> None:
        self.aborted.append(request_id)


def test_abort_session_requests_aborts_engine_with_active_id() -> None:
    engine = _DummyEngine()
    handler = SessionHandler(chat_engine=engine)
    state = _make_state(active_request_id="req-123")

    asyncio.run(handler.abort_session_requests(state))

    assert engine.aborted == ["req-123"]
    assert state.active_request_id is None
