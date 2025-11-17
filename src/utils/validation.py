"""Validation utilities for input normalization and checks."""

from typing import Optional
import re
from ..config import PERSONALITY_MAX_LEN


def normalize_gender(val: Optional[str]) -> Optional[str]:
    """Normalize gender input to standardized values ('female'|'male')."""
    if val is None:
        return None
    v = val.strip().lower()
    if v == "female":
        return "female"
    if v == "male":
        return "male"
    return None


def is_gender_empty_or_null(val: Optional[str]) -> bool:
    """Check if gender is empty or null (before normalization)."""
    if val is None:
        return True
    if not val.strip():
        return True
    return False


_LETTERS_ONLY_RE = re.compile(r"^[A-Za-z]+$")


def normalize_personality(val: Optional[str]) -> Optional[str]:
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
    if not _LETTERS_ONLY_RE.match(v):
        return None
    return v.lower()


def is_personality_empty_or_null(val: Optional[str]) -> bool:
    """Check if personality is empty or null (before normalization)."""
    if val is None:
        return True
    if not val.strip():
        return True
    return False


def validate_personality(personality: Optional[str]) -> bool:
    return normalize_personality(personality) is not None


__all__ = [
    "normalize_gender",
    "is_gender_empty_or_null",
    "validate_personality",
    "normalize_personality",
    "is_personality_empty_or_null",
]
