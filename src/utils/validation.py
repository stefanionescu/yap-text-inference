"""Validation utilities for input normalization and checks."""

from typing import Optional
from ..config import ALLOWED_PERSONALITIES


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


def validate_personality(personality: Optional[str]) -> bool:
    if not personality:
        return False
    return personality.strip() in ALLOWED_PERSONALITIES


__all__ = [
    "normalize_gender",
    "validate_personality",
]
