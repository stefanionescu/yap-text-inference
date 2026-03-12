"""Timeouts and buffering configuration.

Centralizes generation timeouts and executor buffering sizes.
Values are sourced from environment variables with sensible defaults.
"""

import os

# Chat/text generation hard timeout in seconds
CHAT_TIMEOUT_S = float(os.getenv("CHAT_TIMEOUT_S", "60"))

# Tool router timeout in seconds
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "3"))

# Timeout for fetching license info from HuggingFace API
try:
    HF_LICENSE_FETCH_TIMEOUT_S = max(1.0, float(os.getenv("HF_LICENSE_FETCH_TIMEOUT", "5")))
except ValueError:
    HF_LICENSE_FETCH_TIMEOUT_S = 5.0


__all__ = [
    "CHAT_TIMEOUT_S",
    "TOOL_TIMEOUT_S",
    "HF_LICENSE_FETCH_TIMEOUT_S",
]
