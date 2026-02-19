"""Unit tests for session request tracking utilities."""

from __future__ import annotations

from src.state.session import SessionState
from src.handlers.session.requests import (
    CANCELLED_SENTINEL,
    set_tool_request,
    set_active_request,
    get_tool_request_id,
    is_request_cancelled,
    clear_tool_request_id,
    cancel_session_requests,
    cleanup_session_requests,
)


def _make_state(**kwargs: str | dict[str, object] | None) -> SessionState:
    defaults: dict[str, str | dict[str, object] | None] = {"session_id": "s1", "meta": {}}
    defaults.update(kwargs)
    return SessionState(**defaults)  # type: ignore[arg-type]


# --- is_request_cancelled ---


def test_is_request_cancelled_none_state() -> None:
    assert is_request_cancelled(None, "req1") is True


def test_is_request_cancelled_sentinel() -> None:
    state = _make_state(active_request_id=CANCELLED_SENTINEL)
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
    assert result == {"active": "", "tool": ""}


def test_cleanup_extracts_and_clears() -> None:
    state = _make_state(active_request_id="a1", tool_request_id="t1")
    result = cleanup_session_requests(state)
    assert result == {"active": "a1", "tool": "t1"}
    assert state.active_request_id is None
    assert state.tool_request_id is None


def test_cleanup_sentinel_active_returns_empty() -> None:
    state = _make_state(active_request_id=CANCELLED_SENTINEL)
    result = cleanup_session_requests(state)
    assert result["active"] == ""


# --- set/get/clear helpers ---


def test_set_active_request() -> None:
    state = _make_state()
    set_active_request(state, "r1")
    assert state.active_request_id == "r1"


def test_set_tool_request() -> None:
    state = _make_state()
    set_tool_request(state, "t1")
    assert state.tool_request_id == "t1"


def test_get_tool_request_id_none_state() -> None:
    assert get_tool_request_id(None) == ""


def test_get_tool_request_id_with_value() -> None:
    state = _make_state(tool_request_id="t1")
    assert get_tool_request_id(state) == "t1"


def test_clear_tool_request_id() -> None:
    state = _make_state(tool_request_id="t1")
    clear_tool_request_id(state)
    assert state.tool_request_id is None


# --- cancel_session_requests ---


def test_cancel_sets_sentinel() -> None:
    state = _make_state(active_request_id="r1")
    cancel_session_requests(state)
    assert state.active_request_id == CANCELLED_SENTINEL
