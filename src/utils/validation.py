"""Validation utilities for input normalization and checks."""

from typing import Optional, Set
from prompts.chat.personality import PERSONALITIES


# Allowed personalities/styles (from prompts.py)
ALLOWED_PERSONALITIES: Set[str] = set(PERSONALITIES.keys())


def normalize_gender(val: Optional[str]) -> Optional[str]:
    """Normalize gender input to standardized values.
    
    Args:
        val: Raw gender string input
        
    Returns:
        Normalized gender value ('woman', 'man') or None if invalid
    """
    if not val:
        return None
    v = val.strip().lower()
    if v in ("woman", "female", "f", "w"):
        return "woman"
    if v in ("man", "male", "m"):
        return "man"
    return None


def validate_persona_style(style: str) -> bool:
    """Check if persona style is allowed.
    
    Args:
        style: Persona style string
        
    Returns:
        True if valid, False otherwise
    """
    return style.strip() in ALLOWED_PERSONALITIES


def validate_user_identity(user_identity: str) -> str:
    """Validate and normalize user identity.
    
    Args:
        user_identity: Raw user identity input
        
    Returns:
        Normalized user identity ('man', 'woman', 'non-binary')
    """
    if user_identity in {"man", "woman", "non-binary"}:
        return user_identity
    return "non-binary"
