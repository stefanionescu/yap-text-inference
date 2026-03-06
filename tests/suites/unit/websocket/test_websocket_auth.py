"""Unit tests for websocket authentication logic."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
import src.handlers.websocket.auth as auth_mod


class _FakeWebSocket:
    def __init__(self, *, headers: dict[str, str], host: str = "127.0.0.1") -> None:
        self.headers = headers
        self.client = SimpleNamespace(host=host)


def _run_auth(headers: dict[str, str]) -> bool:
    ws = _FakeWebSocket(headers=headers)
    return asyncio.run(auth_mod.authenticate_websocket(ws))


def setup_function() -> None:
    auth_mod._AUTH_FAILURES.clear()


def test_auth_accepts_x_api_key(monkeypatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    assert _run_auth({"x-api-key": "secret"}) is True


def test_auth_accepts_bearer_header(monkeypatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    assert _run_auth({"authorization": "Bearer secret"}) is True


def test_auth_rejects_query_only_key(monkeypatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    assert _run_auth({}) is False


def test_auth_rejects_disallowed_origin(monkeypatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    monkeypatch.setattr(auth_mod, "WS_ALLOWED_ORIGINS", ("https://allowed.example",))
    assert _run_auth({"x-api-key": "secret", "origin": "https://denied.example"}) is False


def test_auth_throttles_repeated_failures(monkeypatch) -> None:
    monkeypatch.setattr(auth_mod, "TEXT_API_KEY", "secret")
    monkeypatch.setattr(auth_mod, "WS_MAX_AUTH_FAILURES_PER_WINDOW", 2)
    monkeypatch.setattr(auth_mod, "WS_AUTH_WINDOW_SECONDS", 60.0)

    assert _run_auth({"x-api-key": "bad"}) is False
    assert _run_auth({"x-api-key": "bad"}) is False

    # Third attempt is throttled even with a valid key.
    assert _run_auth({"x-api-key": "secret"}) is False
