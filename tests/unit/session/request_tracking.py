"""Unit tests for session request tracking utilities."""

from __future__ import annotations

from src.state.session import SessionState
from src.handlers.session.requests import (
    CANCELLED_SENTINEL,
    is_request_cancelled,
    cancel_session_requests,
    cleanup_session_requests,
)


def _make_state(**kwargs: str | dict[str, object] | None) -> SessionState:
    defaults: dict[str, str | dict[str, object] | None] = {"meta": {}}
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
    assert result == {"active": ""}


def test_cleanup_extracts_and_clears() -> None:
    state = _make_state(active_request_id="a1")
    result = cleanup_session_requests(state)
    assert result == {"active": "a1"}
    assert state.active_request_id is None


def test_cleanup_sentinel_active_returns_empty() -> None:
    state = _make_state(active_request_id=CANCELLED_SENTINEL)
    result = cleanup_session_requests(state)
    assert result["active"] == ""


# --- cancel_session_requests ---


def test_cancel_sets_sentinel() -> None:
    state = _make_state(active_request_id="r1")
    cancel_session_requests(state)
    assert state.active_request_id == CANCELLED_SENTINEL
