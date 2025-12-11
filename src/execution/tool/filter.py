"""Pre-filters for tool calls to avoid unnecessary model invocations.

This module coordinates pattern matching across different tool types.
Each tool type has its own module with specific patterns:
- freestyle.py: Freestyle-related patterns (start_freestyle, stop_freestyle)
- screenshot.py: Screenshot-related patterns (take_screenshot)
"""

from typing import Literal

from .freestyle import match_freestyle_phrase
from .screenshot import match_screenshot_phrase

FilterResult = Literal["no_screenshot", "take_screenshot", "start_freestyle", "stop_freestyle", "pass"]


def filter_tool_phrase(user_utt: str) -> FilterResult:
    """
    Check if user utterance matches known patterns for early return.
    
    Delegates to specialized matchers for each tool type.
    Order matters: freestyle is checked before screenshot.
    
    Returns:
        "no_screenshot" - return [] without calling model
        "take_screenshot" - return [{"name": "take_screenshot"}] without calling model
        "start_freestyle" - return [{"name": "start_freestyle"}] without calling model
        "stop_freestyle" - return [{"name": "stop_freestyle"}] without calling model
        "pass" - continue to call the model
    """
    text = user_utt.strip()
    
    # Check freestyle patterns FIRST
    freestyle_result = match_freestyle_phrase(text)
    if freestyle_result == "start":
        return "start_freestyle"
    if freestyle_result == "stop":
        return "stop_freestyle"
    
    # Check screenshot patterns
    screenshot_result = match_screenshot_phrase(text)
    if screenshot_result is not None:
        return screenshot_result
    
    return "pass"
