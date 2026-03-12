"""Unit tests for websocket helper utilities."""

from __future__ import annotations

import uuid
import pytest
import asyncio
import contextlib
from typing import TypedDict
from urllib.parse import urlsplit
from tests.state import SessionContext
from tests.support.helpers.websocket import ws as ws_helpers, build_start_payload, resolve_start_payload_mode


class _ResolveStartPayloadModeKwargs(TypedDict, total=False):
    deploy_mode: str | None
    deploy_chat: bool | None
    deploy_tool: bool | None


def _build_async_receiver(method_name: str, value: str):
    async def _receiver(_self):
        return value

    return type("Receiver", (), {method_name: _receiver})()


def test_with_api_key_normalizes_scheme_and_path() -> None:
    url = ws_helpers.with_api_key("http://localhost:8000", api_key="abc123")

    parts = urlsplit(url)
    assert parts.scheme == "ws"
    assert parts.netloc == "localhost:8000"
    assert parts.path == "/ws"
    assert parts.query == ""


def test_with_api_key_preserves_existing_query_unchanged() -> None:
    url = ws_helpers.with_api_key(
        "ws://localhost:8000/custom?foo=1&api_key=old",
        api_key="new",
    )

    parts = urlsplit(url)
    assert parts.path == "/custom"
    assert parts.query == "foo=1&api_key=old"


def test_build_api_key_headers_uses_x_api_key() -> None:
    headers = ws_helpers.build_api_key_headers(api_key="abc123")
    assert headers == {"X-API-Key": "abc123"}


def test_with_api_key_requires_key_when_missing() -> None:
    missing_env_var = f"TEXT_API_KEY_TEST_ONLY_{uuid.uuid4().hex}"

    with pytest.raises(ValueError, match="TEXT_API_KEY"):
        ws_helpers.with_api_key("ws://localhost:8000/ws", api_key_env=missing_env_var)


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


def test_build_start_payload_includes_chat_fields_in_all_mode() -> None:
    ctx = SessionContext(
        session_id="sess-1",
        gender="female",
        personality="playful",
        chat_prompt="You are concise.",
        sampling={"temperature": 0.7},
        start_payload_mode="all",
    )

    payload = build_start_payload(ctx, "hello")

    assert payload["gender"] == "female"
    assert payload["personality"] == "playful"
    assert payload["chat_prompt"] == "You are concise."
    assert payload["sampling"] == {"temperature": 0.7}


def test_build_start_payload_includes_chat_fields_in_chat_only_mode() -> None:
    ctx = SessionContext(
        session_id="sess-2",
        gender="male",
        personality="calm",
        chat_prompt="Stay direct.",
        sampling={"top_p": 0.9},
        start_payload_mode="chat-only",
    )

    payload = build_start_payload(ctx, "hello")

    assert payload["gender"] == "male"
    assert payload["personality"] == "calm"
    assert payload["chat_prompt"] == "Stay direct."
    assert payload["sampling"] == {"top_p": 0.9}


def test_build_start_payload_omits_chat_fields_in_tool_only_mode() -> None:
    ctx = SessionContext(
        session_id="sess-3",
        gender="female",
        personality="savage",
        chat_prompt="Do not send this.",
        sampling={"temperature": 0.1},
        start_payload_mode="tool-only",
    )

    payload = build_start_payload(ctx, "check the screen")

    assert payload["type"] == "start"
    assert payload["user_utterance"] == "check the screen"
    assert payload["history"] == []
    assert "gender" not in payload
    assert "personality" not in payload
    assert "chat_prompt" not in payload
    assert "sampling" not in payload


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"deploy_mode": "both"}, "all"),
        ({"deploy_mode": "chat"}, "chat-only"),
        ({"deploy_mode": "tool"}, "tool-only"),
        ({"deploy_chat": True, "deploy_tool": True}, "all"),
        ({"deploy_chat": True, "deploy_tool": False}, "chat-only"),
        ({"deploy_chat": False, "deploy_tool": True}, "tool-only"),
        ({}, "all"),
    ],
)
def test_resolve_start_payload_mode_maps_deploy_settings(
    kwargs: _ResolveStartPayloadModeKwargs,
    expected: str,
) -> None:
    typed_kwargs = _ResolveStartPayloadModeKwargs(**kwargs)
    assert (
        resolve_start_payload_mode(
            deploy_mode=typed_kwargs.get("deploy_mode"),
            deploy_chat=typed_kwargs.get("deploy_chat"),
            deploy_tool=typed_kwargs.get("deploy_tool"),
        )
        == expected
    )
