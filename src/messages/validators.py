"""Shared validation helpers for message handlers."""

from __future__ import annotations

from collections.abc import Callable

try:
    from pygments.lexers import guess_lexer  # type: ignore[import-not-found]
    from pygments.util import ClassNotFound  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - pygments is optional
    guess_lexer = None
    ClassNotFound = Exception  # type: ignore[assignment]

from ..config import (
    CODE_DETECTION_MIN_LENGTH,
    CODE_FENCES,
    CODE_LEXER_KEYWORDS,
    PERSONALITY_MAX_LEN,
    SAFE_LEXER_NAMES,
    SCREEN_PREFIX_MAX_CHARS,
)
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


def _has_code_fences(text: str) -> bool:
    """Check for markdown-style code fences."""
    return any(fence in text for fence in CODE_FENCES)


def _looks_like_code_block(text: str) -> bool:
    """Detect executable code using Pygments lexer detection."""
    if not text:
        return False
    
    # Quick check for code fences
    if _has_code_fences(text):
        return True
    
    # Use Pygments to detect if it's code
    if not guess_lexer:
        return False
    
    # Skip very short text that's unlikely to be code
    if len(text.strip()) < CODE_DETECTION_MIN_LENGTH:
        return False
    
    try:
        lexer = guess_lexer(text)
        lexer_name = getattr(lexer, "name", "").lower()
        aliases = {alias.lower() for alias in getattr(lexer, "aliases", [])}
        all_names = {lexer_name, *aliases}
        
        # If it's in our safe list, it's definitely not code
        if any(name in SAFE_LEXER_NAMES for name in all_names):
            return False
        
        # Only flag as code if Pygments detected an actual programming language
        # Check if any lexer name/alias contains programming language keywords
        return any(
            keyword in name for name in all_names for keyword in CODE_LEXER_KEYWORDS
        )
    except ClassNotFound:
        # Pygments couldn't detect a language, assume it's not code
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

