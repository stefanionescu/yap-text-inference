"""Timeouts and buffering configuration.

Centralizes generation timeouts, session TTLs, and executor buffering sizes.
Values are sourced from environment variables with sensible defaults.
"""

import os

# Chat/text generation hard timeout in seconds
GEN_TIMEOUT_S = float(os.getenv("GEN_TIMEOUT_S", "60"))

# Tool router (classifier) timeout in seconds
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "10"))

# Sessions are evicted after this many seconds of inactivity
SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "1800"))


__all__ = [
    "GEN_TIMEOUT_S",
    "TOOL_TIMEOUT_S",
    "SESSION_IDLE_TTL_SECONDS",
]


