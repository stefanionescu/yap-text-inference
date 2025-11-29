"""Shared validation helpers for message handlers."""

from __future__ import annotations

from collections.abc import Callable
import re

from ..config import PERSONALITY_MAX_LEN
from ..utils import (
    sanitize_prompt,
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
            "gender is required and cannot be empty",
        )
    gender = normalize_gender(raw_gender)
    if gender is None:
        raise ValidationError(
            "invalid_gender",
            "gender must be 'female' or 'male'",
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


SCREEN_PREFIX_MAX_CHARS = 30

_CODE_SENTINEL_REGEXES: tuple[re.Pattern[str], ...] = (
    re.compile(r"```|~~~"),
    re.compile(r"<\s*/?\s*script\b", re.IGNORECASE),
    re.compile(r"<\?php", re.IGNORECASE),
    re.compile(r"#!\s*/bin", re.IGNORECASE),
    re.compile(r"\b(from\s+[A-Za-z0-9_.]+\s+import\s+[A-Za-z0-9_*, ]+)\b", re.IGNORECASE),
    re.compile(r"\bimport\s+[A-Za-z0-9_.]+\b", re.IGNORECASE),
    re.compile(r"\b(def|class|function)\s+[A-Za-z0-9_]+\s*\(", re.IGNORECASE),
    re.compile(r"\bconsole\.log\s*\(", re.IGNORECASE),
    re.compile(r"\b(var|let|const)\s+[A-Za-z0-9_]+\s*=", re.IGNORECASE),
    re.compile(r"\bSystem\.[A-Za-z]+\s*\(", re.IGNORECASE),
    re.compile(r"\bpublic\s+static\s+void\b", re.IGNORECASE),
    re.compile(r"\bSELECT\s+.+\s+FROM\b", re.IGNORECASE),
    re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE),
    re.compile(r"\bsudo\s+\S+", re.IGNORECASE),
    re.compile(r"\brm\s+-rf\b", re.IGNORECASE),
)


def _looks_like_code_block(text: str) -> bool:
    """Heuristic detection for embedded code or executable snippets."""
    for pattern in _CODE_SENTINEL_REGEXES:
        if pattern.search(text):
            return True
    suspicious_lines = 0
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("//") or stripped.startswith("#include"):
            return True
        if stripped.endswith((";", "{", "}")):
            suspicious_lines += 1
        if "return " in stripped or stripped.startswith("return"):
            suspicious_lines += 1
        if suspicious_lines >= 2:
            return True
    return False


def ensure_text_is_not_code(*, text: str, field_label: str, error_code: str) -> None:
    """Raise ValidationError if the provided text appears to contain code."""
    if not text:
        return
    if _looks_like_code_block(text):
        raise ValidationError(
            error_code,
            f"{field_label} appears to contain executable code or scripts, which is not allowed.",
        )


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
    ensure_text_is_not_code(
        text=prompt,
        field_label=field_label,
        error_code=invalid_error_code,
    )
    return prompt


def validate_optional_prefix(
    value: str | None,
    *,
    field_label: str,
    invalid_error_code: str,
) -> str | None:
    """Validate an optional short prefix string supplied by clients."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValidationError(invalid_error_code, f"{field_label} must be a string")
    if not value.strip():
        return None
    try:
        sanitized = sanitize_prompt(value, max_chars=SCREEN_PREFIX_MAX_CHARS)
    except ValueError as exc:
        raise ValidationError(invalid_error_code, str(exc)) from exc
    ensure_text_is_not_code(
        text=sanitized,
        field_label=field_label,
        error_code=invalid_error_code,
    )
    return sanitized


__all__ = [
    "ValidationError",
    "validate_required_gender",
    "validate_required_personality",
    "require_prompt",
    "sanitize_prompt_with_limit",
    "validate_optional_prefix",
]

