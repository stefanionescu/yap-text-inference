"""Shared validation helpers for message handlers."""

from __future__ import annotations

from typing import Callable

from ..config import PERSONALITY_MAX_LEN
from ..utils.sanitize import sanitize_prompt
from ..utils.validation import (
    is_gender_empty_or_null,
    is_personality_empty_or_null,
    normalize_gender,
    normalize_personality,
)


class ValidationError(Exception):
    """Structured validation failure with error code metadata."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


def validate_required_gender(raw_gender: str | None) -> str:
    if is_gender_empty_or_null(raw_gender):
        raise ValidationError(
            "missing_gender",
            "assistant_gender is required and cannot be empty",
        )
    gender = normalize_gender(raw_gender)
    if gender is None:
        raise ValidationError(
            "invalid_gender",
            "assistant_gender must be 'female' or 'male'",
        )
    return gender


def validate_required_personality(raw_personality: str | None) -> str:
    if is_personality_empty_or_null(raw_personality):
        raise ValidationError(
            "missing_personality",
            "personality is required and cannot be empty",
        )
    normalized = normalize_personality(raw_personality)
    if normalized is None:
        raise ValidationError(
            "invalid_personality",
            f"personality must be letters-only and lower than or equal to {PERSONALITY_MAX_LEN} characters",
        )
    return normalized


def require_prompt(
    raw_prompt: str | None,
    *,
    error_code: str,
    message: str,
) -> str:
    if not raw_prompt:
        raise ValidationError(error_code, message)
    return raw_prompt


def sanitize_prompt_with_limit(
    raw_prompt: str,
    *,
    field_label: str,
    invalid_error_code: str,
    too_long_error_code: str,
    max_tokens: int,
    count_tokens_fn: Callable[[str], int],
) -> str:
    try:
        prompt = sanitize_prompt(raw_prompt)
    except ValueError as exc:
        raise ValidationError(invalid_error_code, str(exc)) from exc

    if count_tokens_fn(prompt) > max_tokens:
        raise ValidationError(
            too_long_error_code,
            f"{field_label} exceeds token limit ({max_tokens})",
        )
    return prompt


__all__ = [
    "ValidationError",
    "validate_required_gender",
    "validate_required_personality",
    "require_prompt",
    "sanitize_prompt_with_limit",
]

