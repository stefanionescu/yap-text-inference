"""Unit tests for deduplicated warning helpers."""

from __future__ import annotations

from src.helpers.dedupe import info_once, warn_once, has_warned, reset_warnings


def test_warn_once_returns_true_first_false_second() -> None:
    reset_warnings()
    assert warn_once("test_key", "msg") is True
    assert warn_once("test_key", "msg") is False


def test_info_once_returns_true_first_false_second() -> None:
    reset_warnings()
    assert info_once("info_key", "msg") is True
    assert info_once("info_key", "msg") is False


def test_has_warned_before_and_after() -> None:
    reset_warnings()
    assert has_warned("check_key") is False
    warn_once("check_key", "msg")
    assert has_warned("check_key") is True


def test_reset_warnings_clears_state() -> None:
    reset_warnings()
    warn_once("reset_key", "msg")
    assert has_warned("reset_key") is True
    reset_warnings()
    assert has_warned("reset_key") is False


def test_warn_and_info_share_key_space() -> None:
    reset_warnings()
    assert warn_once("shared", "msg") is True
    # info_once with same key should return False since key is already emitted
    assert info_once("shared", "msg") is False
