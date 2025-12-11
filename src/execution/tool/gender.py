"""Gender switch phrase patterns and matching logic."""

import re
from typing import Literal

# Male identifiers (with typo handling via optional chars)
# guy/gu, him, male/mal, hunk, dude/dud, boy/bo, marc, mark, marck
_MALE = r"(guy?|him|male?|hunk|dude?|boy?|marc|mark|marck)"

# Female identifiers (with typo handling via optional chars)
# gal/ga, girl/gir, female, femme, ana, anna, annan
_FEMALE = r"(gal?|girl?|female|femme|ana|anna|annan)"

# Patterns that TRIGGER switch_gender male
MALE_PATTERNS = [
    rf"^switch\s+to\s+{_MALE}[.!?]*$",  # switch to guy
    rf"^change\s+to\s+{_MALE}[.!?]*$",  # change to guy
]

# Compiled male patterns (case insensitive)
_MALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in MALE_PATTERNS]

# Patterns that TRIGGER switch_gender female
FEMALE_PATTERNS = [
    rf"^switch\s+to\s+{_FEMALE}[.!?]*$",  # switch to gal
    rf"^change\s+to\s+{_FEMALE}[.!?]*$",  # change to gal
]

# Compiled female patterns (case insensitive)
_FEMALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in FEMALE_PATTERNS]


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
