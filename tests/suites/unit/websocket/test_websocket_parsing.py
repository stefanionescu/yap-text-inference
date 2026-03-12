"""Unit tests for websocket client message parsing."""

from __future__ import annotations

import json
import pytest
from src.handlers.websocket.parser import parse_client_message
from src.config.websocket import WS_PROTOCOL_VERSION, WS_MAX_MESSAGE_BYTES


def _valid_start(**overrides: object) -> str:
    base: dict[str, object] = {
        "type": "start",
        "v": WS_PROTOCOL_VERSION,
        "gender": "female",
        "personality": "calm",
        "chat_prompt": "hello",
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
        parse_client_message(json.dumps({"v": WS_PROTOCOL_VERSION, "gender": "female"}))


def test_missing_protocol_version_raises() -> None:
    with pytest.raises(ValueError, match="Invalid payload field 'start.v'"):
        parse_client_message(json.dumps({"type": "start", "gender": "female"}))


def test_wrong_protocol_version_raises() -> None:
    with pytest.raises(ValueError, match="unsupported protocol version"):
        parse_client_message(json.dumps({"type": "start", "v": WS_PROTOCOL_VERSION + 1, "gender": "female"}))


def test_valid_start_normalizes_type() -> None:
    result = parse_client_message(_valid_start(type="START"))
    assert result["type"] == "start"


def test_valid_start_returns_all_fields() -> None:
    result = parse_client_message(_valid_start())
    assert result["type"] == "start"
    assert result["v"] == WS_PROTOCOL_VERSION
    assert result["gender"] == "female"
    assert "user_utterance" not in result


def test_start_accepts_large_history_item_count() -> None:
    payload = _valid_start(
        history=[{"role": "user", "content": f"turn {index}"} for index in range(500)],
    )

    result = parse_client_message(payload)

    assert len(result["history"]) == 500
    assert result["history"][0]["content"] == "turn 0"
    assert result["history"][-1]["content"] == "turn 499"


def test_start_accepts_large_history_content_when_message_fits_byte_limit() -> None:
    history = [{"role": "user", "content": "x" * 60000}]
    payload = _valid_start(history=history)

    assert len(payload.encode("utf-8")) < WS_MAX_MESSAGE_BYTES

    result = parse_client_message(payload)

    assert result["history"] == history


def test_start_rejects_user_utterance_field() -> None:
    with pytest.raises(ValueError, match="user_utterance"):
        parse_client_message(_valid_start(user_utterance="hello"))


def test_message_payload_allows_user_utterance() -> None:
    result = parse_client_message(json.dumps({"type": "message", "v": WS_PROTOCOL_VERSION, "user_utterance": "hello"}))
    assert result["type"] == "message"
    assert result["user_utterance"] == "hello"


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValueError, match="custom_field"):
        parse_client_message(
            json.dumps(
                {
                    "type": "start",
                    "v": WS_PROTOCOL_VERSION,
                    "gender": "male",
                    "personality": "calm",
                    "chat_prompt": "hello",
                    "custom_field": "value",
                }
            )
        )


def test_message_payload_size_limit() -> None:
    huge = "x" * 70000
    with pytest.raises(ValueError, match="exceeds max size"):
        parse_client_message(huge)
