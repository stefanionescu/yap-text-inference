"""Freestyle-related phrase patterns and matching logic."""

import re
from typing import Literal

# Flexible pattern for "freestyle" with common typos:
# - freestyle (correct)
# - frestyle (missing 'e')
# - frestile (missing 'e', 'i' instead of 'y')
# - freeestile (extra 'e', 'i' instead of 'y')
_FREESTYLE = r"fre+st[iy]le?"

# Patterns that TRIGGER start_freestyle
START_PATTERNS = [
    rf"^start\s+{_FREESTYLE}[.!?]*$",  # start freestyle
    rf"^start\s+{_FREESTYLE}\s+\w+[.!?]*$",  # start freestyle bro
    rf"^can\s+you\s+start\s+{_FREESTYLE}[.!?]*$",  # can you start freestyle?
    rf"^please\s+start\s+{_FREESTYLE}[.!?]*$",  # please start freestyle
    rf"^please\s+start\s+{_FREESTYLE}\s+\w+[.!?]*$",  # please start freestyle bro
    rf"^mind\s+starting\s+{_FREESTYLE}[.!?]*$",  # mind starting freestyle
    rf"^mind\s+starting\s+{_FREESTYLE}\s+\w+[.!?]*$",  # mind starting freestyle bro
    rf"^just\s+start\s+{_FREESTYLE}[.!?]*$",  # just start freestyle
    rf"^just\s+start\s+{_FREESTYLE}\s+already[.!?]*$",  # just start freestyle already
]

# Compiled start patterns (case insensitive)
_START_COMPILED = [re.compile(p, re.IGNORECASE) for p in START_PATTERNS]

# Patterns that TRIGGER stop_freestyle
STOP_PATTERNS = [
    rf"^stop\s+{_FREESTYLE}[.!?]*$",  # stop freestyle
    rf"^stop\s+{_FREESTYLE}\s+\w+[.!?]*$",  # stop freestyle bro
    rf"^stopping\s+{_FREESTYLE}[.!?]*$",  # stopping freestyle
    rf"^can\s+you\s+stop\s+{_FREESTYLE}[.!?]*$",  # can you stop freestyle?
    rf"^please\s+stop\s+{_FREESTYLE}[.!?]*$",  # please stop freestyle
    rf"^please\s+stop\s+{_FREESTYLE}\s+\w+[.!?]*$",  # please stop freestyle bro
    rf"^mind\s+stop(?:ping)?\s+{_FREESTYLE}[.!?]*$",  # mind stop/stopping freestyle
    rf"^mind\s+stop(?:ping)?\s+{_FREESTYLE}\s+\w+[.!?]*$",  # mind stop/stopping freestyle bro
    rf"^just\s+stop\s+{_FREESTYLE}[.!?]*$",  # just stop freestyle
    rf"^just\s+stop\s+{_FREESTYLE}\s+already[.!?]*$",  # just stop freestyle already
]

# Compiled stop patterns (case insensitive)
_STOP_COMPILED = [re.compile(p, re.IGNORECASE) for p in STOP_PATTERNS]


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
