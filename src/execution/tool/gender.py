"""Gender switch phrase matching logic."""

import re
from typing import Literal

from ...config.tool_patterns import (
    GENDER_MALE_PATTERNS,
    GENDER_FEMALE_PATTERNS,
)

# Compiled patterns (case insensitive)
_MALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in GENDER_MALE_PATTERNS]
_FEMALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in GENDER_FEMALE_PATTERNS]


def match_gender_phrase(text: str) -> Literal["male", "female", None]:
    """
    Check if text matches gender switch patterns.
    
    Args:
        text: Stripped/normalized user utterance
        
    Returns:
        "male" - matches a male switch pattern
        "female" - matches a female switch pattern
        None - no match, continue to other checks
    """
    # Check male patterns
    for pattern in _MALE_COMPILED:
        if pattern.match(text):
            return "male"
    
    # Check female patterns
    for pattern in _FEMALE_COMPILED:
        if pattern.match(text):
            return "female"
    
    return None
