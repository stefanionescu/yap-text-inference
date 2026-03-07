"""Unit tests for websocket authentication logic."""

from __future__ import annotations

import time
import asyncio
from collections import deque
from types import SimpleNamespace
from collections.abc import Callable
import src.handlers.websocket.auth as auth_mod


class _FakeWebSocket:
    def __init__(self, *, headers: dict[str, str], host: str = "127.0.0.1") -> None:
        self.headers = headers
        self.client = SimpleNamespace(host=host)


def _run_auth(
    headers: dict[str, str],
    *,
    auth_config: auth_mod.AuthRuntimeConfig,
    auth_failures: dict[str, deque[float]],
    now_fn: Callable[[], float] = time.monotonic,
) -> bool:
    ws = _FakeWebSocket(headers=headers)
    return asyncio.run(
        auth_mod.authenticate_websocket(
            ws,
            auth_config=auth_config,
            auth_failures=auth_failures,
            now_fn=now_fn,
        )
    )


def _auth_config(
    *,
    key: str = "secret",
    allowed_origins: tuple[str, ...] = (),
    max_failures: int = 20,
    window_seconds: float = 60.0,
) -> auth_mod.AuthRuntimeConfig:
    return auth_mod.AuthRuntimeConfig(
        text_api_key=key,
        allowed_origins=allowed_origins,
        max_auth_failures_per_window=max_failures,
        auth_window_seconds=window_seconds,
    )


def test_auth_accepts_x_api_key() -> None:
    assert _run_auth({"x-api-key": "secret"}, auth_config=_auth_config(), auth_failures={}) is True


def test_auth_accepts_bearer_header() -> None:
    assert _run_auth({"authorization": "Bearer secret"}, auth_config=_auth_config(), auth_failures={}) is True


def test_auth_rejects_query_only_key() -> None:
    assert _run_auth({}, auth_config=_auth_config(), auth_failures={}) is False


def test_auth_rejects_disallowed_origin() -> None:
    config = _auth_config(allowed_origins=("https://allowed.example",))
    assert (
        _run_auth(
            {"x-api-key": "secret", "origin": "https://denied.example"},
            auth_config=config,
            auth_failures={},
        )
        is False
    )


def test_auth_throttles_repeated_failures() -> None:
    config = _auth_config(max_failures=2, window_seconds=60.0)
    failures: dict[str, deque[float]] = {}

    def fixed_now() -> float:
        return 100.0

    assert _run_auth({"x-api-key": "bad"}, auth_config=config, auth_failures=failures, now_fn=fixed_now) is False
    assert _run_auth({"x-api-key": "bad"}, auth_config=config, auth_failures=failures, now_fn=fixed_now) is False

    # Third attempt is throttled even with a valid key.
    assert _run_auth({"x-api-key": "secret"}, auth_config=config, auth_failures=failures, now_fn=fixed_now) is False
