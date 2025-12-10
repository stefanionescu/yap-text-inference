"""Timeouts and buffering configuration.

Centralizes generation timeouts and executor buffering sizes.
Values are sourced from environment variables with sensible defaults.
"""

import os


# Chat/text generation hard timeout in seconds
GEN_TIMEOUT_S = float(os.getenv("GEN_TIMEOUT_S", "60"))

# Tool router (classifier) timeout in seconds
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "10"))


__all__ = [
    "GEN_TIMEOUT_S",
    "TOOL_TIMEOUT_S",
]


