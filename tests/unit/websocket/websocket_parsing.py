"""Unit tests for websocket client message parsing."""

from __future__ import annotations

import json

import pytest

from src.handlers.websocket.parser import parse_client_message


def _valid_msg(**overrides: str | dict[str, str]) -> str:
    base: dict[str, str | dict[str, str]] = {
        "type": "start",
        "session_id": "s1",
        "request_id": "r1",
        "payload": {"prompt": "hello"},
    }
    base.update(overrides)
    return json.dumps(base)


def test_empty_message_raises() -> None:
    with pytest.raises(ValueError, match="Empty message"):
        parse_client_message("")


def test_whitespace_message_raises() -> None:
    with pytest.raises(ValueError, match="Empty message"):
        parse_client_message("   ")


def test_invalid_json_raises() -> None:
    with pytest.raises(ValueError, match="valid JSON"):
        parse_client_message("{bad json")


def test_non_object_string_raises() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_client_message('"hello"')


def test_non_object_array_raises() -> None:
    with pytest.raises(ValueError, match="JSON object"):
        parse_client_message("[1, 2]")


def test_missing_type_raises() -> None:
    with pytest.raises(ValueError, match="Missing 'type'"):
        parse_client_message(json.dumps({"session_id": "s", "request_id": "r", "payload": {}}))


def test_missing_session_id_raises() -> None:
    with pytest.raises(ValueError, match="Missing 'session_id'"):
        parse_client_message(json.dumps({"type": "start", "request_id": "r", "payload": {}}))


def test_missing_request_id_raises() -> None:
    with pytest.raises(ValueError, match="Missing 'request_id'"):
        parse_client_message(json.dumps({"type": "start", "session_id": "s", "payload": {}}))


def test_missing_payload_raises() -> None:
    with pytest.raises(ValueError, match="Missing 'payload'"):
        parse_client_message(json.dumps({"type": "start", "session_id": "s", "request_id": "r"}))


def test_non_dict_payload_raises() -> None:
    with pytest.raises(ValueError, match="'payload' must be a JSON object"):
        parse_client_message(json.dumps({"type": "start", "session_id": "s", "request_id": "r", "payload": "text"}))


def test_valid_message_normalizes_type() -> None:
    result = parse_client_message(_valid_msg(type="START"))
    assert result["type"] == "start"


def test_valid_message_returns_all_keys() -> None:
    result = parse_client_message(_valid_msg())
    assert result["type"] == "start"
    assert result["session_id"] == "s1"
    assert result["request_id"] == "r1"
    assert result["payload"] == {"prompt": "hello"}
