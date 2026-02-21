"""Unit tests for websocket disconnect classification helpers."""

from __future__ import annotations

from fastapi import WebSocketDisconnect
from src.handlers.websocket.disconnects import is_expected_ws_disconnect


def test_is_expected_disconnect_for_websocket_disconnect() -> None:
    assert is_expected_ws_disconnect(WebSocketDisconnect(code=1000))


def test_is_expected_disconnect_for_connection_reset_error() -> None:
    assert is_expected_ws_disconnect(ConnectionResetError("peer reset"))


def test_is_expected_disconnect_for_disconnect_runtime_error_message() -> None:
    err = RuntimeError('Cannot call "receive" once a disconnect message has been received.')
    assert is_expected_ws_disconnect(err)


def test_is_expected_disconnect_false_for_generic_runtime_error() -> None:
    err = RuntimeError("boom")
    assert not is_expected_ws_disconnect(err)
