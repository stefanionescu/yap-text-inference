"""Freestyle-related phrase matching logic."""

import re
from typing import Literal

from ...config.tool import (
    FREESTYLE_START_PATTERNS,
    FREESTYLE_STOP_PATTERNS,
)

# Compiled patterns (case insensitive)
_START_COMPILED = [re.compile(p, re.IGNORECASE) for p in FREESTYLE_START_PATTERNS]
_STOP_COMPILED = [re.compile(p, re.IGNORECASE) for p in FREESTYLE_STOP_PATTERNS]


def match_freestyle_phrase(text: str) -> Literal["start", "stop", None]:
    """
    Check if text matches freestyle-related patterns.
    
    Args:
        text: Stripped/normalized user utterance
        
    Returns:
        "start" - matches a start freestyle pattern
        "stop" - matches a stop freestyle pattern
        None - no match, continue to other checks
    """
    # Check start patterns
    for pattern in _START_COMPILED:
        if pattern.match(text):
            return "start"
    
    # Check stop patterns
    for pattern in _STOP_COMPILED:
        if pattern.match(text):
            return "stop"
    
    return None
