"""Unit tests for sampling parameter extraction and validation."""

from __future__ import annotations

import pytest
from src.errors import ValidationError
import src.messages.sampling as sampling_mod
from src.messages.sampling import _coerce_int, _coerce_float, extract_sampling_overrides

# --- _coerce_float ---


def test_coerce_float_from_int() -> None:
    assert _coerce_float(1) == 1.0


def test_coerce_float_from_string() -> None:
    assert _coerce_float("0.5") == 0.5


def test_coerce_float_bool_raises() -> None:
    with pytest.raises(TypeError):
        _coerce_float(True)


def test_coerce_float_empty_string_raises() -> None:
    with pytest.raises(ValueError):
        _coerce_float("")


# --- _coerce_int ---


def test_coerce_int_from_int() -> None:
    assert _coerce_int(1) == 1


def test_coerce_int_from_integer_float() -> None:
    assert _coerce_int(1.0) == 1


def test_coerce_int_from_non_integer_float_raises() -> None:
    with pytest.raises(ValueError):
        _coerce_int(1.5)


def test_coerce_int_bool_raises() -> None:
    with pytest.raises(TypeError):
        _coerce_int(True)


# --- extract_sampling_overrides ---


def test_extract_empty_msg_returns_empty() -> None:
    result = extract_sampling_overrides({}, deploy_chat=True)
    assert result == {}


def test_extract_valid_temperature() -> None:
    low = sampling_mod.CHAT_TEMPERATURE_MIN
    result = extract_sampling_overrides({"temperature": low}, deploy_chat=True)
    assert "temperature" in result
    assert result["temperature"] == float(low)


def test_extract_temperature_out_of_range() -> None:
    with pytest.raises(ValidationError, match="temperature must be between"):
        extract_sampling_overrides({"temperature": 999.0}, deploy_chat=True)


def test_extract_bool_temperature_raises() -> None:
    with pytest.raises(ValidationError, match="temperature must be a valid"):
        extract_sampling_overrides({"temperature": True}, deploy_chat=True)


def test_extract_nested_sampling_block() -> None:
    low = sampling_mod.CHAT_TEMPERATURE_MIN
    result = extract_sampling_overrides({"sampling": {"temperature": low}}, deploy_chat=True)
    assert result["temperature"] == float(low)


def test_extract_sanitize_output_boolean() -> None:
    result = extract_sampling_overrides({"sanitize_output": False}, deploy_chat=True)
    assert result["sanitize_output"] is False


def test_extract_non_dict_sampling_block_raises() -> None:
    with pytest.raises(ValidationError, match="sampling must be an object"):
        extract_sampling_overrides({"sampling": "not_a_dict"}, deploy_chat=True)


def test_extract_returns_empty_when_deploy_chat_false() -> None:
    result = extract_sampling_overrides({"temperature": 0.5}, deploy_chat=False)
    assert result == {}
