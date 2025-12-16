"""Pre-filters for tool calls to avoid unnecessary model invocations.

This module provides fast regex-based pattern matching to detect common
user commands without invoking the classifier model. This improves latency
for known patterns and reduces GPU load.

Supported Patterns:

1. Freestyle Mode:
   - "start freestyle" / "enable freestyle"
   - "stop freestyle" / "disable freestyle"

2. Gender Switching:
   - "switch to male" / "be a guy"
   - "switch to female" / "be a girl"

3. Personality Switching:
   - "change personality to X" / "be more X"
   - Combined: "be a X Y" (e.g., "be a male assistant")

4. Screenshot Commands:
   - "take a screenshot" / "screenshot this"
   - Rejection patterns: "don't take screenshot"
   - Quantity patterns: "take 2 screenshots" -> no

Patterns are compiled at module load time for efficiency.
Case-insensitive matching is used throughout.

The filter returns a FilterResult with:
- action: What to do (take_screenshot, switch_gender, etc., or "pass")
- param: Optional first parameter (gender, personality name)
- param2: Optional second parameter (for combined commands)
"""

import re
from dataclasses import dataclass
from typing import Literal

from ...config.patterns import (
    FREESTYLE_START_PATTERNS,
    FREESTYLE_STOP_PATTERNS,
    GENDER_MALE_PATTERNS,
    GENDER_FEMALE_PATTERNS,
    SCREENSHOT_REJECT_PATTERNS,
    SCREENSHOT_TAKE_X_PATTERN,
    SCREENSHOT_TRIGGER_QUANTITIES,
    SCREENSHOT_TRIGGER_PATTERNS,
)
from .personality import match_personality_phrase, match_gender_personality_phrase

# =============================================================================
# Compiled Patterns (module-level for efficiency)
# Patterns are compiled once at import time to avoid repeated compilation.
# =============================================================================

# Freestyle patterns
_FREESTYLE_START_COMPILED = [re.compile(p, re.IGNORECASE) for p in FREESTYLE_START_PATTERNS]
_FREESTYLE_STOP_COMPILED = [re.compile(p, re.IGNORECASE) for p in FREESTYLE_STOP_PATTERNS]

# Gender patterns
_GENDER_MALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in GENDER_MALE_PATTERNS]
_GENDER_FEMALE_COMPILED = [re.compile(p, re.IGNORECASE) for p in GENDER_FEMALE_PATTERNS]

# Screenshot patterns
_SCREENSHOT_REJECT_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_REJECT_PATTERNS]
_SCREENSHOT_TAKE_X_COMPILED = re.compile(SCREENSHOT_TAKE_X_PATTERN, re.IGNORECASE)
_SCREENSHOT_TRIGGER_COMPILED = [re.compile(p, re.IGNORECASE) for p in SCREENSHOT_TRIGGER_PATTERNS]

# =============================================================================
# Types
# =============================================================================

StaticFilterResult = Literal[
    "no_screenshot",
    "take_screenshot",
    "start_freestyle",
    "stop_freestyle",
    "pass",
]


@dataclass(slots=True, frozen=True)
class FilterResult:
    """Result of tool phrase filtering.
    
    Immutable dataclass containing the filter decision and any
    extracted parameters.
    
    Attributes:
        action: The detected action, one of:
            - "pass": No pattern matched, continue to classifier
            - "no_screenshot": Explicit rejection pattern matched
            - "take_screenshot": Screenshot trigger matched
            - "start_freestyle" / "stop_freestyle": Freestyle commands
            - "switch_gender": Gender switch with param=gender
            - "switch_personality": Personality switch with param=name
            - "switch_gender_and_personality": Combined with param=gender, param2=name
        param: First parameter extracted from pattern.
        param2: Second parameter for combined commands.
    """
    
    action: StaticFilterResult | Literal["switch_gender", "switch_personality", "switch_gender_and_personality"]
    """The action to take based on the matched pattern."""
    
    param: str | None = None
    """Optional parameter (e.g., personality name for switch_personality)."""
    
    param2: str | None = None
    """Second parameter (e.g., gender for switch_gender_and_personality)."""


# =============================================================================
# Pattern Matchers
# =============================================================================

def _match_freestyle(text: str) -> Literal["start", "stop"] | None:
    """Check if text matches freestyle start/stop patterns."""
    for pattern in _FREESTYLE_START_COMPILED:
        if pattern.match(text):
            return "start"
    for pattern in _FREESTYLE_STOP_COMPILED:
        if pattern.match(text):
            return "stop"
    return None


def _match_gender(text: str) -> Literal["male", "female"] | None:
    """Check if text matches gender switch patterns."""
    for pattern in _GENDER_MALE_COMPILED:
        if pattern.match(text):
            return "male"
    for pattern in _GENDER_FEMALE_COMPILED:
        if pattern.match(text):
            return "female"
    return None


def _match_screenshot(text: str) -> Literal["take_screenshot", "no_screenshot"] | None:
    """Check if text matches screenshot patterns."""
    # Check reject patterns first
    for pattern in _SCREENSHOT_REJECT_COMPILED:
        if pattern.match(text):
            return "no_screenshot"
    
    # Check "take X screenshot(s)" pattern
    match = _SCREENSHOT_TAKE_X_COMPILED.match(text)
    if match:
        quantity = match.group(1).lower()
        if quantity in SCREENSHOT_TRIGGER_QUANTITIES:
            return "take_screenshot"
        return "no_screenshot"
    
    # Check trigger patterns (typos, direct commands)
    for pattern in _SCREENSHOT_TRIGGER_COMPILED:
        if pattern.match(text):
            return "take_screenshot"
    
    return None


# =============================================================================
# Main Filter
# =============================================================================

def filter_tool_phrase(
    user_utt: str,
    personalities: dict[str, list[str]] | None = None,
) -> FilterResult:
    """
    Check if user utterance matches known patterns for early return.
    
    Args:
        user_utt: The user utterance to check
        personalities: Optional dict mapping personality names to synonyms
        
    Returns:
        FilterResult with action and optional param
    """
    text = user_utt.strip()
    
    # Check freestyle patterns
    freestyle_result = _match_freestyle(text)
    if freestyle_result == "start":
        return FilterResult(action="start_freestyle")
    if freestyle_result == "stop":
        return FilterResult(action="stop_freestyle")
    
    # Check combined gender + personality patterns FIRST (more specific)
    combined_result = match_gender_personality_phrase(text, personalities)
    if combined_result is not None:
        gender, personality = combined_result
        return FilterResult(action="switch_gender_and_personality", param=gender, param2=personality)
    
    # Check gender patterns (only if not combined)
    gender_result = _match_gender(text)
    if gender_result is not None:
        return FilterResult(action="switch_gender", param=gender_result)
    
    # Check personality patterns (requires personalities config)
    personality_result = match_personality_phrase(text, personalities)
    if personality_result is not None:
        return FilterResult(action="switch_personality", param=personality_result)
    
    # Check screenshot patterns
    screenshot_result = _match_screenshot(text)
    if screenshot_result is not None:
        return FilterResult(action=screenshot_result)
    
    return FilterResult(action="pass")


__all__ = ["filter_tool_phrase", "FilterResult"]
