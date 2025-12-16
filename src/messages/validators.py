"""Shared validation helpers for message handlers."""

from __future__ import annotations

from collections.abc import Callable

from ..config import (
    PERSONALITY_MAX_LEN,
    SCREEN_PREFIX_MAX_CHARS,
)
from ..config.limits import (
    MAX_PERSONALITIES,
    MAX_SYNONYMS_PER_PERSONALITY,
)
from ..utils import sanitize_prompt
from ..helpers.input import (
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
    return sanitized


def validate_personalities_list(
    raw_personalities: dict | list | None,
) -> dict[str, list[str]] | None:
    """Validate and normalize the personalities configuration.
    
    Expected format (dict):
    {
        "friendly": ["generic", "normal"],
        "flirty": ["horny", "sexy"],
        "religious": [],
        "delulu": []
    }
    
    Keys are personality names, values are lists of synonyms (can be empty).
    All names and synonyms are lowercased and must be non-empty strings.
    
    Limits:
    - Max MAX_PERSONALITIES entries (default 50)
    - Max MAX_SYNONYMS_PER_PERSONALITY synonyms per personality (default 10)
    
    Returns:
        Normalized dict mapping personality -> list of synonyms, or None if not provided.
        
    Raises:
        ValidationError: If the format is invalid.
    """
    if raw_personalities is None:
        return None
    
    if not isinstance(raw_personalities, dict):
        raise ValidationError(
            "invalid_personalities_format",
            "personalities must be an object mapping personality names to synonym arrays"
        )
    
    if not raw_personalities:
        raise ValidationError(
            "empty_personalities",
            "personalities cannot be empty - at least one personality is required"
        )
    
    if len(raw_personalities) > MAX_PERSONALITIES:
        raise ValidationError(
            "too_many_personalities",
            f"personalities cannot exceed {MAX_PERSONALITIES} entries"
        )
    
    normalized: dict[str, list[str]] = {}
    all_names: set[str] = set()  # Track all names + synonyms for uniqueness
    
    for key, synonyms in raw_personalities.items():
        # Validate key
        if not isinstance(key, str) or not key.strip():
            raise ValidationError(
                "invalid_personality_name",
                "personality names must be non-empty strings"
            )
        
        personality_name = key.strip().lower()
        
        if personality_name in all_names:
            raise ValidationError(
                "duplicate_personality",
                f"duplicate personality name: '{personality_name}'"
            )
        all_names.add(personality_name)
        
        # Validate synonyms
        if not isinstance(synonyms, list):
            raise ValidationError(
                "invalid_personality_synonyms",
                f"synonyms for '{personality_name}' must be an array"
            )
        
        if len(synonyms) > MAX_SYNONYMS_PER_PERSONALITY:
            raise ValidationError(
                "too_many_synonyms",
                f"personality '{personality_name}' cannot have more than {MAX_SYNONYMS_PER_PERSONALITY} synonyms"
            )
        
        normalized_synonyms: list[str] = []
        for synonym in synonyms:
            if not isinstance(synonym, str) or not synonym.strip():
                raise ValidationError(
                    "invalid_personality_synonym",
                    f"synonyms for '{personality_name}' must be non-empty strings"
                )
            
            syn_lower = synonym.strip().lower()
            
            if syn_lower in all_names:
                raise ValidationError(
                    "duplicate_personality_synonym",
                    f"duplicate synonym '{syn_lower}' - already used as personality or synonym"
                )
            all_names.add(syn_lower)
            normalized_synonyms.append(syn_lower)
        
        normalized[personality_name] = normalized_synonyms
    
    return normalized


def validate_personality_in_list(
    personality: str,
    personalities: dict[str, list[str]] | None,
) -> None:
    """Validate that the given personality exists in the personalities list.
    
    The personality can be either a main personality name or one of its synonyms.
    
    Args:
        personality: The personality to check (already normalized/lowercased)
        personalities: The validated personalities dict
        
    Raises:
        ValidationError: If personality is not found in the list
    """
    if personalities is None:
        return
    
    # Build set of all valid personality names (main + synonyms)
    valid_names: set[str] = set()
    for name, synonyms in personalities.items():
        valid_names.add(name)
        valid_names.update(synonyms)
    
    if personality not in valid_names:
        raise ValidationError(
            "personality_not_in_list",
            f"personality '{personality}' must be one of the available personalities or their synonyms"
        )


__all__ = [
    "ValidationError",
    "validate_required_gender",
    "validate_required_personality",
    "validate_personalities_list",
    "validate_personality_in_list",
    "require_prompt",
    "sanitize_prompt_with_limit",
    "validate_optional_prefix",
]

