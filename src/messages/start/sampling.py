"""Sampling parameter extraction and validation.

This module handles the extraction and validation of sampling parameters
from incoming WebSocket messages. Supported parameters:

- temperature: Controls randomness (float)
- top_p: Nucleus sampling threshold (float)
- top_k: Top-K sampling limit (int)
- min_p: Minimum probability threshold (float)
- repetition_penalty: Repetition penalty factor (float)
- presence_penalty: Presence penalty factor (float)
- frequency_penalty: Frequency penalty factor (float)
- sanitize_output: Whether to sanitize output (bool)

Each parameter is validated against configured min/max bounds and
type-checked before being included in the overrides dict.
"""

from __future__ import annotations

from typing import Any

from ..validators import ValidationError
from ...config import (
    DEPLOY_CHAT,
    CHAT_MIN_P_MAX,
    CHAT_MIN_P_MIN,
    CHAT_TOP_K_MAX,
    CHAT_TOP_K_MIN,
    CHAT_TOP_P_MAX,
    CHAT_TOP_P_MIN,
    CHAT_TEMPERATURE_MAX,
    CHAT_TEMPERATURE_MIN,
    CHAT_PRESENCE_PENALTY_MAX,
    CHAT_PRESENCE_PENALTY_MIN,
    CHAT_FREQUENCY_PENALTY_MAX,
    CHAT_FREQUENCY_PENALTY_MIN,
    CHAT_REPETITION_PENALTY_MAX,
    CHAT_REPETITION_PENALTY_MIN,
)

# Sampling field configuration: (name, type, min, max, invalid_code, range_code)
_SAMPLING_FIELDS: tuple[tuple[str, type, float | int, float | int, str, str], ...] = (
    (
        "temperature",
        float,
        CHAT_TEMPERATURE_MIN,
        CHAT_TEMPERATURE_MAX,
        "invalid_temperature",
        "temperature_out_of_range",
    ),
    ("top_p", float, CHAT_TOP_P_MIN, CHAT_TOP_P_MAX, "invalid_top_p", "top_p_out_of_range"),
    ("top_k", int, CHAT_TOP_K_MIN, CHAT_TOP_K_MAX, "invalid_top_k", "top_k_out_of_range"),
    ("min_p", float, CHAT_MIN_P_MIN, CHAT_MIN_P_MAX, "invalid_min_p", "min_p_out_of_range"),
    (
        "repetition_penalty",
        float,
        CHAT_REPETITION_PENALTY_MIN,
        CHAT_REPETITION_PENALTY_MAX,
        "invalid_repetition_penalty",
        "repetition_penalty_out_of_range",
    ),
    (
        "presence_penalty",
        float,
        CHAT_PRESENCE_PENALTY_MIN,
        CHAT_PRESENCE_PENALTY_MAX,
        "invalid_presence_penalty",
        "presence_penalty_out_of_range",
    ),
    (
        "frequency_penalty",
        float,
        CHAT_FREQUENCY_PENALTY_MIN,
        CHAT_FREQUENCY_PENALTY_MAX,
        "invalid_frequency_penalty",
        "frequency_penalty_out_of_range",
    ),
)


def _coerce_sampling_value(value: Any, caster: type) -> float | int:
    """Coerce a raw value to the target sampling type."""
    if caster is int:
        return _coerce_int(value)
    return _coerce_float(value)


def _coerce_float(value: Any) -> float:
    """Coerce a value to float, rejecting bools and invalid types."""
    if isinstance(value, bool):
        raise TypeError("bool not allowed")
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("empty string")
        return float(stripped)
    raise TypeError("unsupported type")


def _coerce_int(value: Any) -> int:
    """Coerce a value to int, rejecting bools and non-integer floats."""
    if isinstance(value, bool):
        raise TypeError("bool not allowed")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError("non-integer float")
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            raise ValueError("empty string")
        return int(stripped)
    raise TypeError("unsupported type")


def extract_sampling_overrides(msg: dict[str, Any]) -> dict[str, float | int | bool]:
    """Extract and validate sampling parameter overrides from a message.

    Looks for parameters in both the top-level message and a nested
    'sampling' or 'sampling_params' block.

    Args:
        msg: The message dict to extract parameters from.

    Returns:
        Dict of validated sampling overrides. Empty if DEPLOY_CHAT is False.

    Raises:
        ValidationError: If any parameter fails type or range validation.
    """
    if not DEPLOY_CHAT:
        return {}

    overrides: dict[str, float | int | bool] = {}
    sampling_block = msg.get("sampling") or msg.get("sampling_params") or {}
    if sampling_block and not isinstance(sampling_block, dict):
        raise ValidationError("invalid_sampling_payload", "sampling must be an object")

    for field, caster, minimum, maximum, invalid_code, range_code in _SAMPLING_FIELDS:
        raw_value = None
        if isinstance(sampling_block, dict):
            raw_value = sampling_block.get(field)
        if raw_value is None:
            raw_value = msg.get(field)
        if raw_value is None:
            continue

        try:
            normalized = _coerce_sampling_value(raw_value, caster)
        except (TypeError, ValueError):
            raise ValidationError(invalid_code, f"{field} must be a valid {caster.__name__}") from None

        if not (minimum <= normalized <= maximum):
            raise ValidationError(
                range_code,
                f"{field} must be between {minimum} and {maximum}",
            )
        overrides[field] = normalized

    # Handle boolean options
    sanitize_raw = sampling_block.get("sanitize_output") if isinstance(sampling_block, dict) else None
    if sanitize_raw is None:
        sanitize_raw = msg.get("sanitize_output")
    if sanitize_raw is not None:
        if not isinstance(sanitize_raw, bool):
            raise ValidationError("invalid_sanitize_output", "sanitize_output must be a boolean")
        overrides["sanitize_output"] = sanitize_raw

    return overrides


__all__ = ["extract_sampling_overrides"]
