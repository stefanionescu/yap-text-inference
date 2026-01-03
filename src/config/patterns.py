"""Centralized screenshot pattern definitions for tool filtering.

The screenshot tool is the only phrase-based shortcut that remains; these
patterns are imported by the tool filter to short-circuit classifier calls.
"""

# Patterns that REJECT screenshot requests (return [] / no tool call)
# "look/check twice/thrice/multiple times" and similar
SCREENSHOT_REJECT_PATTERNS = [
    r"^look\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+multiple\s+times[.!?]*$",
    r"^check\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+multiple\s+times[.!?]*$",
]

# Pattern for "take X screenshot(s)" - captures X
SCREENSHOT_TAKE_X_PATTERN = r"^take\s+(\w+)\s+screenshots?[.!?]*$"

# Values of X that trigger a screenshot (singular)
SCREENSHOT_TRIGGER_QUANTITIES = {"one", "1", "once", "a"}

# Patterns that TRIGGER screenshot (return [{"name": "take_screenshot"}])
SCREENSHOT_TRIGGER_PATTERNS = [
    r"^take\s+screenshots?[.!?]*$",  # "take screenshot", "take screenshots"
    r"^screenshot\s+this[.!?]*$",  # "screenshot this"
    r"^sceenshot\s+this[.!?]*$",  # typo: "sceenshot this"
    r"^lok\s+at\s+this[.!?]*$",  # typo: "lok at this"
    r"^lock\s+at\s+this[.!?]*$",  # typo: "lock at this"
    r"^tkae\s+a\s+look[.!?]*$",  # typo: "tkae a look"
    r"^teak\s+a\s+look[.!?]*$",  # typo: "teak a look"
]

__all__ = [
    "SCREENSHOT_REJECT_PATTERNS",
    "SCREENSHOT_TAKE_X_PATTERN",
    "SCREENSHOT_TRIGGER_QUANTITIES",
    "SCREENSHOT_TRIGGER_PATTERNS",
]
