"""Unit tests for websocket authentication helpers."""

from __future__ import annotations

import pytest

import src.handlers.websocket.auth as auth_mod
from src.handlers.websocket.auth import _select_api_key, validate_api_key, _validate_candidate


def test_validate_api_key_correct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret123")
    assert validate_api_key("secret123") is True


def test_validate_api_key_wrong(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret123")
    assert validate_api_key("wrong") is False


def test_select_api_key_returns_first_non_empty() -> None:
    assert _select_api_key("first", "second") == "first"


def test_select_api_key_skips_none() -> None:
    assert _select_api_key(None, None, "key3") == "key3"


def test_select_api_key_all_none() -> None:
    assert _select_api_key(None, None) is None


def test_validate_candidate_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    ok, key, error = _validate_candidate(None, context="test")
    assert ok is False
    assert key is None
    assert error == "missing"


def test_validate_candidate_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    ok, key, error = _validate_candidate("wrong", context="test")
    assert ok is False
    assert key is None
    assert error == "invalid"


def test_validate_candidate_correct(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    ok, key, error = _validate_candidate("secret", context="test")
    assert ok is True
    assert key == "secret"
    assert error is None
