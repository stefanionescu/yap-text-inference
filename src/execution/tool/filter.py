"""Pre-filters for tool calls to avoid unnecessary model invocations.

This module coordinates pattern matching across different tool types.
Each tool type has its own module with specific patterns:
- freestyle.py: Freestyle-related patterns (start_freestyle, stop_freestyle)
- gender.py: Gender switch patterns (switch_gender male/female)
- personality.py: Personality switch patterns (switch_personality)
- screenshot.py: Screenshot-related patterns (take_screenshot)
"""

from dataclasses import dataclass
from typing import Literal

from .freestyle import match_freestyle_phrase
from .gender import match_gender_phrase
from .personality import match_personality_phrase
from .screenshot import match_screenshot_phrase

# Static filter results (no parameter needed)
StaticFilterResult = Literal[
    "no_screenshot",
    "take_screenshot",
    "start_freestyle",
    "stop_freestyle",
    "switch_gender_male",
    "switch_gender_female",
    "pass",
]


@dataclass(slots=True, frozen=True)
class FilterResult:
    """Result of tool phrase filtering."""
    
    action: StaticFilterResult | Literal["switch_personality"]
    """The action to take based on the matched pattern."""
    
    param: str | None = None
    """Optional parameter (e.g., personality name for switch_personality)."""


def filter_tool_phrase(
    user_utt: str,
    personalities: dict[str, list[str]] | None = None,
) -> FilterResult:
    """
    Check if user utterance matches known patterns for early return.
    
    Delegates to specialized matchers for each tool type.
    
    Args:
        user_utt: The user utterance to check
        personalities: Optional dict mapping personality names to synonyms
        
    Returns:
        FilterResult with action and optional param:
        - action="no_screenshot" - return [] without calling model
        - action="take_screenshot" - return [{"name": "take_screenshot"}]
        - action="start_freestyle" - return [{"name": "start_freestyle"}]
        - action="stop_freestyle" - return [{"name": "stop_freestyle"}]
        - action="switch_gender_male" - return [{"name": "switch_gender", "param": "male"}]
        - action="switch_gender_female" - return [{"name": "switch_gender", "param": "female"}]
        - action="switch_personality", param=name - return [{"name": "switch_personality", "param": name}]
        - action="pass" - continue to call the model
    """
    text = user_utt.strip()
    
    # Check freestyle patterns
    freestyle_result = match_freestyle_phrase(text)
    if freestyle_result == "start":
        return FilterResult(action="start_freestyle")
    if freestyle_result == "stop":
        return FilterResult(action="stop_freestyle")
    
    # Check gender patterns
    gender_result = match_gender_phrase(text)
    if gender_result == "male":
        return FilterResult(action="switch_gender_male")
    if gender_result == "female":
        return FilterResult(action="switch_gender_female")
    
    # Check personality patterns (requires personalities config)
    personality_result = match_personality_phrase(text, personalities)
    if personality_result is not None:
        return FilterResult(action="switch_personality", param=personality_result)
    
    # Check screenshot patterns
    screenshot_result = match_screenshot_phrase(text)
    if screenshot_result is not None:
        return FilterResult(action=screenshot_result)
    
    return FilterResult(action="pass")
