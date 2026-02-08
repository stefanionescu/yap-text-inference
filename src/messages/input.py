"""Input normalization and validation helpers.

Provides utilities for normalizing and validating user input fields
like gender and personality. Used by message validators.
"""

from src.config.limits import PERSONALITY_MAX_LEN
from src.config.filters import LETTERS_ONLY_PATTERN


def normalize_gender(val: str | None) -> str | None:
    """Normalize gender input to standardized values ('female'|'male')."""
    if val is None:
        return None
    v = val.strip().lower()
    if v == "female":
        return "female"
    if v == "male":
        return "male"
    return None


def is_gender_empty_or_null(val: str | None) -> bool:
    """Check if gender is empty or null (before normalization)."""
    return val is None or not val.strip()


def normalize_personality(val: str | None) -> str | None:
    """Normalize personality: letters-only, length-limited, lowercased.

    Returns lowercase personality or None if invalid.
    """
    if val is None:
        return None
    v = val.strip()
    if not v:
        return None
    if len(v) > PERSONALITY_MAX_LEN:
        return None
    if not LETTERS_ONLY_PATTERN.match(v):
        return None
    return v.lower()


def is_personality_empty_or_null(val: str | None) -> bool:
    """Check if personality is empty or null (before normalization)."""
    return val is None or not val.strip()


__all__ = [
    "normalize_gender",
    "is_gender_empty_or_null",
    "normalize_personality",
    "is_personality_empty_or_null",
]
