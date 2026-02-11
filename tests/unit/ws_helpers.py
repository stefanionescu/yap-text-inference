"""Unit tests for websocket helper utilities."""

from __future__ import annotations

import asyncio
import contextlib
from urllib.parse import parse_qs, urlsplit

import pytest

from tests.helpers.websocket import ws as ws_helpers


def _build_async_receiver(method_name: str, value: str):
    async def _receiver(_self):
        return value

    return type("Receiver", (), {method_name: _receiver})()


def test_with_api_key_normalizes_scheme_path_and_query() -> None:
    url = ws_helpers.with_api_key("http://localhost:8000", api_key="abc123")

    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert parts.scheme == "ws"
    assert parts.netloc == "localhost:8000"
    assert parts.path == "/ws"
    assert query == {"api_key": ["abc123"]}


def test_with_api_key_preserves_query_and_replaces_existing_key() -> None:
    url = ws_helpers.with_api_key(
        "ws://localhost:8000/custom?foo=1&api_key=old",
        api_key="new",
    )

    parts = urlsplit(url)
    query = parse_qs(parts.query)
    assert parts.path == "/custom"
    assert query == {"foo": ["1"], "api_key": ["new"]}


def test_with_api_key_requires_key_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TEXT_API_KEY", raising=False)

    with pytest.raises(ValueError, match="TEXT_API_KEY"):
        ws_helpers.with_api_key("ws://localhost:8000/ws")


def test_recv_raw_uses_receive_if_available() -> None:
    receiver = _build_async_receiver("receive", "payload-from-receive")

    value = asyncio.run(ws_helpers.recv_raw(receiver))

    assert value == "payload-from-receive"


def test_recv_raw_uses_recv_when_receive_is_unavailable() -> None:
    receiver = _build_async_receiver("recv", "payload-from-recv")

    value = asyncio.run(ws_helpers.recv_raw(receiver))

    assert value == "payload-from-recv"


def test_connect_with_retries_succeeds_after_transient_failures() -> None:
    attempts = {"count": 0}

    def _factory():
        attempts["count"] += 1
        attempt = attempts["count"]

        @contextlib.asynccontextmanager
        async def _manager():
            if attempt < 3:
                raise RuntimeError("connect failed")
            yield {"attempt": attempt}

        return _manager()

    async def _run() -> None:
        async with ws_helpers.connect_with_retries(_factory, max_retries=2, base_delay_s=0.0) as connection:
            assert connection["attempt"] == 3

    asyncio.run(_run())
    assert attempts["count"] == 3


def test_connect_with_retries_raises_after_retry_limit() -> None:
    attempts = {"count": 0}

    def _factory():
        attempts["count"] += 1

        @contextlib.asynccontextmanager
        async def _manager():
            raise RuntimeError("still failing")
            yield

        return _manager()

    async def _run() -> None:
        with pytest.raises(RuntimeError, match="still failing"):
            async with ws_helpers.connect_with_retries(_factory, max_retries=1, base_delay_s=0.0):
                pass

    asyncio.run(_run())
    assert attempts["count"] == 2


def test_connect_with_retries_does_not_retry_after_successful_connect() -> None:
    attempts = {"count": 0}

    def _factory():
        attempts["count"] += 1

        @contextlib.asynccontextmanager
        async def _manager():
            yield {"attempt": attempts["count"]}

        return _manager()

    async def _run() -> None:
        with pytest.raises(ValueError, match="boom"):
            async with ws_helpers.connect_with_retries(_factory, max_retries=2, base_delay_s=0.0):
                raise ValueError("boom")

    asyncio.run(_run())
    assert attempts["count"] == 1
