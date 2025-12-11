"""Screenshot-related phrase matching logic."""

import re
from typing import Literal

from ...config.tool_patterns import (
    SCREENSHOT_REJECT_PATTERNS,
    SCREENSHOT_TAKE_X_PATTERN,
    SCREENSHOT_TRIGGER_QUANTITIES,
    SCREENSHOT_TRIGGER_PATTERNS,
)

# Compiled patterns (case insensitive)
_REJECT_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_REJECT_PATTERNS]
_TAKE_X_COMPILED = re.compile(SCREENSHOT_TAKE_X_PATTERN, re.IGNORECASE)
_TRIGGER_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_TRIGGER_PATTERNS]


def match_screenshot_phrase(text: str) -> Literal["take_screenshot", "no_screenshot", None]:
    """
    Check if text matches screenshot-related patterns.
    
    Args:
        text: Stripped/normalized user utterance
        
    Returns:
        "take_screenshot" - matches a trigger pattern (take screenshot)
        "no_screenshot" - matches a reject pattern (no screenshot)
        None - no match, continue to other checks
    """
    # Check reject patterns first
    for pattern in _REJECT_COMPILED:
        if pattern.match(text):
            return "no_screenshot"
    
    # Check "take X screenshot(s)" pattern
    match = _TAKE_X_COMPILED.match(text)
    if match:
        quantity = match.group(1).lower()
        if quantity in SCREENSHOT_TRIGGER_QUANTITIES:
            return "take_screenshot"
        else:
            # Any other quantity (two, three, multiple, etc.) -> no_screenshot
            return "no_screenshot"
    
    # Check trigger patterns (typos, direct commands)
    for pattern in _TRIGGER_COMPILED:
        if pattern.match(text):
            return "take_screenshot"
    
    return None
