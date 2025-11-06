"""Validation utilities for input normalization and checks."""

from typing import Optional
import re
from ..config import PERSONALITY_MAX_LEN


def normalize_gender(val: Optional[str]) -> Optional[str]:
    """Normalize gender input to standardized values ('female'|'male')."""
    if not val:
        return None
    v = val.strip().lower()
    if v in ("woman", "female", "f", "w"):
        return "female"
    if v in ("man", "male", "m"):
        return "male"
    return None


_LETTERS_ONLY_RE = re.compile(r"^[A-Za-z]+$")


def normalize_personality(val: Optional[str]) -> Optional[str]:
    """Normalize personality: letters-only, length-limited, lowercased.

    Returns lowercase personality or None if invalid.
    """
    if not val:
        return None
    v = val.strip()
    if not v:
        return None
    if len(v) > PERSONALITY_MAX_LEN:
        return None
    if not _LETTERS_ONLY_RE.match(v):
        return None
    return v.lower()


def validate_personality(personality: Optional[str]) -> bool:
    return normalize_personality(personality) is not None


__all__ = [
    "normalize_gender",
    "validate_personality",
    "normalize_personality",
]
