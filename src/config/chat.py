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
# RESPONSE MESSAGES
# ============================================================================

# Hard-coded messages for message rate limit responses
MESSAGE_RATE_LIMIT_MESSAGES: tuple[str, ...] = (
    "Wow you yap a lot, slow down a bit.",
    "I'm a bit overwhelmed sorry, give me a moment to recover.",
    "Damn you really talk a lot, give me a second to recover.",
    "My head's spinning, you're sending too many messages."
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
    "MESSAGE_RATE_LIMIT_MESSAGES",
    "DIGIT_WORDS",
]

