"""Integration tests for websocket cancel and recovery behavior."""

from __future__ import annotations

import json
import asyncio
import typing as t
from src.server import create_app
import src.messages.turn as turn_mod
from tests.state import SessionContext
from fastapi.testclient import TestClient
from src.runtime.dependencies import RuntimeDeps
from src.handlers.connections import ConnectionHandler
from src.handlers.session.manager import SessionHandler
import src.handlers.websocket.manager as websocket_manager
from contextlib import AbstractContextManager, contextmanager
from src.handlers.websocket.helpers import stream_chat_response
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.handlers.session.history.settings import HistoryRuntimeConfig
from tests.support.helpers.websocket import build_start_payload, build_cancel_payload, build_message_payload


def _history_config() -> HistoryRuntimeConfig:
    return HistoryRuntimeConfig(
        deploy_chat=True,
        deploy_tool=False,
        chat_trigger_tokens=1000,
        chat_target_tokens=800,
        default_tool_history_tokens=None,
    )


def _build_runtime_deps() -> tuple[RuntimeDeps, AbstractContextManager[object]]:
    tokenizer_cm = use_local_tokenizers()
    tokenizer = tokenizer_cm.__enter__()
    session_handler = SessionHandler(
        chat_engine=None,
        chat_tokenizer=tokenizer,
        history_config=_history_config(),
    )
    runtime_deps = RuntimeDeps(
        connections=ConnectionHandler(max_connections=4),
        session_handler=session_handler,
        chat_engine=None,
        cache_reset_manager=None,
        tool_adapter=None,
        chat_tokenizer=tokenizer,
        tool_tokenizer=None,
    )
    return runtime_deps, tokenizer_cm


@contextmanager
def _test_client(monkeypatch) -> t.Iterator[TestClient]:
    async def _allow_auth(*_args, **_kwargs) -> bool:
        return True

    async def _fake_dispatch_execution(ws, plan, runtime_deps: RuntimeDeps) -> None:
        chunks_by_prompt = {
            "cancel me": ("cancel-alpha", "cancel-beta"),
            "recover now": ("recover-alpha", "recover-beta"),
        }
        first, second = chunks_by_prompt.get(plan.chat_user_utt or "", ("generic-alpha", "generic-beta"))

        async def _stream():
            yield first
            await asyncio.sleep(0.05)
            yield second

        await stream_chat_response(
            ws,
            _stream(),
            plan.state,
            plan.chat_user_utt or "",
            history_user_utt=plan.chat_user_utt or "",
            history_turn_id=plan.history_turn_id,
            session_handler=runtime_deps.session_handler,
        )

    monkeypatch.setattr(websocket_manager, "authenticate_websocket", _allow_auth)
    monkeypatch.setattr(turn_mod, "dispatch_execution", _fake_dispatch_execution)

    runtime_deps, tokenizer_cm = _build_runtime_deps()
    app = create_app(attach_lifecycle=False, validate_environment=False)
    app.state.runtime_deps = runtime_deps

    try:
        with TestClient(app) as client:
            yield client
    finally:
        tokenizer_cm.__exit__(None, None, None)


def _receive_json(ws) -> dict[str, object]:
    return json.loads(ws.receive_text())


def _build_ctx() -> SessionContext:
    return SessionContext(
        session_id="integration-cancel",
        gender="female",
        personality="calm",
        chat_prompt="Stay concise.",
        start_payload_mode="all",
    )


def test_start_bootstraps_then_cancelled_turn_recovers_cleanly(monkeypatch) -> None:
    with _test_client(monkeypatch) as client, client.websocket_connect("/ws") as ws:
        ctx = _build_ctx()

        ws.send_text(json.dumps(build_start_payload(ctx)))
        bootstrap_done = _receive_json(ws)
        assert bootstrap_done == {"type": "done", "status": 200}

        ws.send_text(json.dumps(build_message_payload("cancel me")))
        first_token = _receive_json(ws)
        assert first_token == {"type": "token", "text": "cancel-alpha"}

        ws.send_text(json.dumps(build_cancel_payload()))
        cancelled = _receive_json(ws)
        assert cancelled == {"type": "cancelled"}

        ws.send_text(json.dumps(build_message_payload("recover now")))
        recovery_token = _receive_json(ws)
        assert recovery_token == {"type": "token", "text": "recover-alpha"}

        second_recovery_token = _receive_json(ws)
        assert second_recovery_token == {"type": "token", "text": "recover-beta"}

        recovery_final = _receive_json(ws)
        assert recovery_final["type"] == "final"
        assert recovery_final["text"] == "recover-alpharecover-beta"

        recovery_done = _receive_json(ws)
        assert recovery_done == {"type": "done", "status": 200}
