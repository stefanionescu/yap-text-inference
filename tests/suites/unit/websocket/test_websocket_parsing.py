"""Unit tests for websocket client message parsing."""

from __future__ import annotations

import json
import pytest
from src.config.websocket import WS_PROTOCOL_VERSION
from src.handlers.websocket.parser import parse_client_message


def _valid_msg(**overrides: object) -> str:
    base: dict[str, object] = {
        "type": "start",
        "v": WS_PROTOCOL_VERSION,
        "gender": "female",
        "user_utterance": "hello",
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
        parse_client_message(json.dumps({"v": WS_PROTOCOL_VERSION, "gender": "female", "user_utterance": "hi"}))


def test_missing_protocol_version_raises() -> None:
    with pytest.raises(ValueError, match="Invalid payload field 'start.v'"):
        parse_client_message(json.dumps({"type": "start", "gender": "female", "user_utterance": "hi"}))


def test_wrong_protocol_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported protocol version"):
        parse_client_message(json.dumps({"type": "start", "v": WS_PROTOCOL_VERSION + 1, "gender": "female"}))


def test_valid_message_normalizes_type() -> None:
    result = parse_client_message(_valid_msg(type="START"))
    assert result["type"] == "start"


def test_valid_message_returns_all_fields() -> None:
    result = parse_client_message(_valid_msg())
    assert result["type"] == "start"
    assert result["v"] == WS_PROTOCOL_VERSION
    assert result["gender"] == "female"
    assert result["user_utterance"] == "hello"


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="custom_field"):
        parse_client_message(
            json.dumps(
                {
                    "type": "start",
                    "v": WS_PROTOCOL_VERSION,
                    "gender": "male",
                    "custom_field": "value",
                }
            )
        )


def test_message_payload_size_limit() -> None:
    huge = "x" * 70000
    with pytest.raises(ValueError, match="exceeds max size"):
        parse_client_message(huge)
