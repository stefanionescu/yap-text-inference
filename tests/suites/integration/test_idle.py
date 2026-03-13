"""Integration tests for websocket idle-timeout behavior."""

from __future__ import annotations

import json
from src.server import create_app
from collections.abc import Iterator
from fastapi.testclient import TestClient
from src.runtime.dependencies import RuntimeDeps
from src.handlers.connections import ConnectionHandler
import src.handlers.websocket.lifecycle as lifecycle_mod
import src.handlers.session.manager as session_manager_mod
import src.handlers.websocket.manager as websocket_manager
from contextlib import AbstractContextManager, contextmanager
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.config.websocket import WS_CLOSE_IDLE_CODE, WS_PROTOCOL_VERSION, WS_CLOSE_IDLE_REASON


def _build_runtime_deps() -> tuple[RuntimeDeps, AbstractContextManager[object]]:
    tokenizer_cm = use_local_tokenizers()
    tokenizer = tokenizer_cm.__enter__()
    runtime_deps = RuntimeDeps(
        connections=ConnectionHandler(max_connections=4),
        session_handler=session_manager_mod.SessionHandler(chat_engine=None, chat_tokenizer=tokenizer),
        chat_engine=None,
        cache_reset_manager=None,
        tool_adapter=None,
        chat_tokenizer=tokenizer,
        tool_tokenizer=None,
    )
    return runtime_deps, tokenizer_cm


@contextmanager
def _test_client(monkeypatch) -> Iterator[TestClient]:
    async def _allow_auth(*_args, **_kwargs) -> bool:
        return True

    def _fast_lifecycle(ws):
        return lifecycle_mod.WebSocketLifecycle(
            ws,
            idle_timeout_s=10.0,
            watchdog_tick_s=0.5,
        )

    monkeypatch.setattr(websocket_manager, "authenticate_websocket", _allow_auth)
    monkeypatch.setattr(websocket_manager, "WebSocketLifecycle", _fast_lifecycle)

    runtime_deps, tokenizer_cm = _build_runtime_deps()
    app = create_app(attach_lifecycle=False, validate_environment=False)
    app.state.runtime_deps = runtime_deps

    try:
        with TestClient(app) as client:
            yield client
    finally:
        tokenizer_cm.__exit__(None, None, None)


def test_idle_connection_closes_with_expected_code_and_reason(monkeypatch) -> None:
    with _test_client(monkeypatch) as client, client.websocket_connect("/ws") as ws:
        close_frame = ws.receive()

    assert close_frame["type"] == "websocket.close"
    assert close_frame["code"] == WS_CLOSE_IDLE_CODE
    assert close_frame["reason"] == WS_CLOSE_IDLE_REASON


def test_activity_keeps_connection_alive_until_explicit_end(monkeypatch) -> None:
    with _test_client(monkeypatch) as client, client.websocket_connect("/ws") as ws:
        ws.send_text(json.dumps({"type": "ping", "v": WS_PROTOCOL_VERSION}))
        assert json.loads(ws.receive_text()) == {"type": "pong"}

        ws.send_text(json.dumps({"type": "end", "v": WS_PROTOCOL_VERSION}))
        assert json.loads(ws.receive_text()) == {"type": "done", "status": 200}
