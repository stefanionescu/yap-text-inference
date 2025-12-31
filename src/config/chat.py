"""Chat behavior configuration.

Prefixes for screenshot flows, cache management, template settings,
and canned response messages.
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag


# ============================================================================
# SCREENSHOT FLOW PREFIXES
# ============================================================================

# Prefixes used to steer chat behavior around screenshot flows
DEFAULT_CHECK_SCREEN_PREFIX = os.getenv("CHECK_SCREEN_PREFIX", "MUST CHECK SCREEN:").strip()
DEFAULT_SCREEN_CHECKED_PREFIX = os.getenv("SCREEN_CHECKED_PREFIX", "ON THE SCREEN NOW:").strip()

# ============================================================================
# TEMPLATE SETTINGS
# ============================================================================

# Enable thinking mode in chat templates
CHAT_TEMPLATE_ENABLE_THINKING = env_flag("CHAT_TEMPLATE_ENABLE_THINKING", False)

# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

CACHE_RESET_INTERVAL_SECONDS = float(os.getenv("CACHE_RESET_INTERVAL_SECONDS", "600"))
CACHE_RESET_MIN_SESSION_SECONDS = float(os.getenv("CACHE_RESET_MIN_SESSION_SECONDS", "300"))

# ============================================================================
# TOOL CONTINUATION
# ============================================================================

# Tool function names that should proceed to chat generation after execution.
# All other tool functions skip chat and return just the tool result.
CHAT_CONTINUE_TOOLS: frozenset[str] = frozenset({"take_screenshot"})

# ============================================================================
# CANNED RESPONSES
# ============================================================================

# Hard-coded messages for control functions (switch_gender, switch_personality, etc.)
# These are cycled per session to ensure variety
CONTROL_FUNCTION_MESSAGES: tuple[str, ...] = (
    "All done",
    "Yup sure. Done.",
    "Alright, gimme a second. Done.",
    "Sure, it's done.",
    "That's done for ya.",
    "Sure thing, done.",
    "Consider it done.",
    "Right away. Done.",
    "There you go.",
    "No problem, done.",
    "Easy, done.",
    "You got it.",
    "Yep, all set.",
    "There ya go.",
    "Cool, all set.",
)

# Hard-coded messages for message rate limit responses
MESSAGE_RATE_LIMIT_MESSAGES: tuple[str, ...] = (
    "Wow you yap a lot, slow down a bit.",
    "I'm a bit overwhelmed sorry, give me a moment to recover.",
    "Damn you really talk a lot, give me a second to recover.",
    "My head's spinning, you're sending too many messages."
)

# Hard-coded messages for chat prompt update rate limit responses
CHAT_PROMPT_RATE_LIMIT_MESSAGES: tuple[str, ...] = (
    "I can't change moods that often, sorry.",
    "I'm not a robot, wait a bit before you change my personality.",
    "Nope sorry, you've changed my mood too many times.",
    "Don't wanna, I'll do it later."
)

# ============================================================================
# TEXT TRANSFORMATION
# ============================================================================

# Digit to word mapping for phone number verbalization in chat output
DIGIT_WORDS: dict[str, str] = {
    "0": "zero",
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "6": "six",
    "7": "seven",
    "8": "eight",
    "9": "nine",
}


__all__ = [
    "DEFAULT_CHECK_SCREEN_PREFIX",
    "DEFAULT_SCREEN_CHECKED_PREFIX",
    "CHAT_TEMPLATE_ENABLE_THINKING",
    "CACHE_RESET_INTERVAL_SECONDS",
    "CACHE_RESET_MIN_SESSION_SECONDS",
    "CHAT_CONTINUE_TOOLS",
    "CONTROL_FUNCTION_MESSAGES",
    "MESSAGE_RATE_LIMIT_MESSAGES",
    "CHAT_PROMPT_RATE_LIMIT_MESSAGES",
    "DIGIT_WORDS",
]

