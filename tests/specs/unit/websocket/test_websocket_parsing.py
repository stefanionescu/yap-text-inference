"""Unit tests for websocket client message parsing."""

from __future__ import annotations

import json
import pytest
from src.handlers.websocket.parser import parse_client_message


def _valid_msg(**overrides: str | dict[str, str]) -> str:
    base: dict[str, str | dict[str, str]] = {
        "type": "start",
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
        parse_client_message(json.dumps({"gender": "female", "user_utterance": "hi"}))


def test_valid_message_normalizes_type() -> None:
    result = parse_client_message(_valid_msg(type="START"))
    assert result["type"] == "start"


def test_valid_message_returns_all_fields() -> None:
    result = parse_client_message(_valid_msg())
    assert result["type"] == "start"
    assert result["gender"] == "female"
    assert result["user_utterance"] == "hello"


def test_extra_fields_pass_through() -> None:
    result = parse_client_message(
        json.dumps(
            {
                "type": "start",
                "gender": "male",
                "custom_field": "value",
            }
        )
    )
    assert result["custom_field"] == "value"
