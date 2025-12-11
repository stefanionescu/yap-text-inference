"""Pre-filters for tool calls to avoid unnecessary model invocations.

This module coordinates pattern matching across different tool types.
Each tool type has its own module with specific patterns:
- freestyle.py: Freestyle-related patterns (start_freestyle, stop_freestyle)
- gender.py: Gender switch patterns (switch_gender male/female)
- screenshot.py: Screenshot-related patterns (take_screenshot)
"""

from typing import Literal

from .freestyle import match_freestyle_phrase
from .gender import match_gender_phrase
from .screenshot import match_screenshot_phrase

FilterResult = Literal[
    "no_screenshot",
    "take_screenshot",
    "start_freestyle",
    "stop_freestyle",
    "switch_gender_male",
    "switch_gender_female",
    "pass",
]


def filter_tool_phrase(user_utt: str) -> FilterResult:
    """
    Check if user utterance matches known patterns for early return.
    
    Delegates to specialized matchers for each tool type.
    
    Returns:
        "no_screenshot" - return [] without calling model
        "take_screenshot" - return [{"name": "take_screenshot"}] without calling model
        "start_freestyle" - return [{"name": "start_freestyle"}] without calling model
        "stop_freestyle" - return [{"name": "stop_freestyle"}] without calling model
        "switch_gender_male" - return [{"name": "switch_gender", "param": "male"}] without calling model
        "switch_gender_female" - return [{"name": "switch_gender", "param": "female"}] without calling model
        "pass" - continue to call the model
    """
    text = user_utt.strip()
    
    # Check freestyle patterns
    freestyle_result = match_freestyle_phrase(text)
    if freestyle_result == "start":
        return "start_freestyle"
    if freestyle_result == "stop":
        return "stop_freestyle"
    
    # Check gender patterns
    gender_result = match_gender_phrase(text)
    if gender_result == "male":
        return "switch_gender_male"
    if gender_result == "female":
        return "switch_gender_female"
    
    # Check screenshot patterns
    screenshot_result = match_screenshot_phrase(text)
    if screenshot_result is not None:
        return screenshot_result
    
    return "pass"
