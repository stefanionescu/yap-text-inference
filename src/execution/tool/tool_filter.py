"""Pre-filters for tool calls to avoid unnecessary model invocations."""

import re
from typing import Literal

# Patterns that return [] (no tool call)
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


def filter_tool_phrase(user_utt: str) -> Literal["reject", "trigger", "pass"]:
    """
    Check if user utterance matches known patterns for early return.
    
    Returns:
        "reject" - return [] without calling model
        "trigger" - return [{"name": "take_screenshot"}] without calling model
        "pass" - continue to call the model
    """
    text = user_utt.strip()
    
    # Check reject patterns
    for pattern in _REJECT_COMPILED:
        if pattern.match(text):
            return "reject"
    
    # Check "take X screenshot(s)" pattern
    match = _TAKE_SCREENSHOTS_PATTERN.match(text)
    if match:
        quantity = match.group(1).lower()
        if quantity in _TRIGGER_QUANTITIES:
            return "trigger"
        else:
            # Any other quantity (two, three, multiple, etc.) -> reject
            return "reject"
    
    return "pass"
