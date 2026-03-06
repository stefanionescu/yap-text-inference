"""Unit tests for sampling parameter extraction and validation."""

from __future__ import annotations

import pytest
from src.errors import ValidationError
import src.messages.start.sampling as sampling_mod
from src.messages.start.sampling import _coerce_int, _coerce_float, extract_sampling_overrides

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


def test_extract_empty_msg_returns_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    result = extract_sampling_overrides({})
    assert result == {}


def test_extract_valid_temperature(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    low = sampling_mod.CHAT_TEMPERATURE_MIN
    result = extract_sampling_overrides({"temperature": low})
    assert "temperature" in result
    assert result["temperature"] == float(low)


def test_extract_temperature_out_of_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    with pytest.raises(ValidationError, match="temperature must be between"):
        extract_sampling_overrides({"temperature": 999.0})


def test_extract_bool_temperature_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    with pytest.raises(ValidationError, match="temperature must be a valid"):
        extract_sampling_overrides({"temperature": True})


def test_extract_nested_sampling_block(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    low = sampling_mod.CHAT_TEMPERATURE_MIN
    result = extract_sampling_overrides({"sampling": {"temperature": low}})
    assert result["temperature"] == float(low)


def test_extract_sanitize_output_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    result = extract_sampling_overrides({"sanitize_output": False})
    assert result["sanitize_output"] is False


def test_extract_non_dict_sampling_block_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", True)
    with pytest.raises(ValidationError, match="sampling must be an object"):
        extract_sampling_overrides({"sampling": "not_a_dict"})


def test_extract_returns_empty_when_deploy_chat_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sampling_mod, "DEPLOY_CHAT", False)
    result = extract_sampling_overrides({"temperature": 0.5})
    assert result == {}
