"""Screenshot-related phrase patterns and matching logic."""

import re
from typing import Literal

# Patterns that REJECT screenshot requests (return [] / no tool call)
# "look/check twice/thrice/multiple times" and similar
REJECT_PATTERNS = [
    r"^look\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+multiple\s+times[.!?]*$",
    r"^check\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+multiple\s+times[.!?]*$",
]

# Compiled reject patterns (case insensitive)
_REJECT_COMPILED = [re.compile(p, re.IGNORECASE) for p in REJECT_PATTERNS]

# Pattern for "take X screenshot(s)" - captures X
_TAKE_SCREENSHOTS_PATTERN = re.compile(
    r"^take\s+(\w+)\s+screenshots?[.!?]*$",
    re.IGNORECASE
)

# Values of X that trigger a screenshot (singular)
_TRIGGER_QUANTITIES = {"one", "1", "once", "a"}

# Patterns that TRIGGER screenshot (return [{"name": "take_screenshot"}])
TRIGGER_PATTERNS = [
    r"^take\s+screenshots?[.!?]*$",  # "take screenshot", "take screenshots"
    r"^screenshot\s+this[.!?]*$",  # "screenshot this"
    r"^sceenshot\s+this[.!?]*$",  # typo: "sceenshot this"
    r"^lok\s+at\s+this[.!?]*$",  # typo: "lok at this"
    r"^lock\s+at\s+this[.!?]*$",  # typo: "lock at this"
    r"^tkae\s+a\s+look[.!?]*$",  # typo: "tkae a look"
    r"^teak\s+a\s+look[.!?]*$",  # typo: "teak a look"
]

# Compiled trigger patterns (case insensitive)
_TRIGGER_COMPILED = [re.compile(p, re.IGNORECASE) for p in TRIGGER_PATTERNS]


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
    match = _TAKE_SCREENSHOTS_PATTERN.match(text)
    if match:
        quantity = match.group(1).lower()
        if quantity in _TRIGGER_QUANTITIES:
            return "take_screenshot"
        else:
            # Any other quantity (two, three, multiple, etc.) -> no_screenshot
            return "no_screenshot"
    
    # Check trigger patterns (typos, direct commands)
    for pattern in _TRIGGER_COMPILED:
        if pattern.match(text):
            return "take_screenshot"
    
    return None
