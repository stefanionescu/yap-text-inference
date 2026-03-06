"""Unit tests for message validation helpers."""

from __future__ import annotations

import pytest
from src.errors import ValidationError
from src.messages.validators import validate_optional_prefix, sanitize_prompt_with_limit

# --- sanitize_prompt_with_limit ---


def test_sanitize_prompt_with_limit_valid() -> None:
    result = sanitize_prompt_with_limit(
        "hello world",
        field_label="prompt",
        invalid_error_code="invalid_prompt",
        too_long_error_code="prompt_too_long",
        max_tokens=100,
        count_tokens_fn=lambda s: len(s.split()),
    )
    assert result == "hello world"


def test_sanitize_prompt_with_limit_invalid_prompt() -> None:
    with pytest.raises(ValidationError):
        sanitize_prompt_with_limit(
            "",
            field_label="prompt",
            invalid_error_code="invalid_prompt",
            too_long_error_code="prompt_too_long",
            max_tokens=100,
            count_tokens_fn=lambda s: len(s.split()),
        )


def test_sanitize_prompt_with_limit_exceeds_tokens() -> None:
    with pytest.raises(ValidationError, match="exceeds token limit"):
        sanitize_prompt_with_limit(
            "hello world foo bar",
            field_label="prompt",
            invalid_error_code="invalid_prompt",
            too_long_error_code="prompt_too_long",
            max_tokens=2,
            count_tokens_fn=lambda s: len(s.split()),
        )


# --- validate_optional_prefix ---


def test_validate_optional_prefix_none() -> None:
    assert validate_optional_prefix(None, field_label="prefix", invalid_error_code="bad_prefix") is None


def test_validate_optional_prefix_whitespace_only() -> None:
    assert validate_optional_prefix("  ", field_label="prefix", invalid_error_code="bad_prefix") is None


def test_validate_optional_prefix_valid() -> None:
    result = validate_optional_prefix("OK:", field_label="prefix", invalid_error_code="bad_prefix")
    assert result is not None
    assert "OK:" in result


def test_validate_optional_prefix_non_string() -> None:
    with pytest.raises(ValidationError, match="must be a string"):
        validate_optional_prefix(123, field_label="prefix", invalid_error_code="bad_prefix")  # type: ignore[arg-type]
