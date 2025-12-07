"""Timeouts and buffering configuration.

Centralizes generation timeouts and executor buffering sizes.
Values are sourced from environment variables with sensible defaults.
"""

import os


# Chat/text generation hard timeout in seconds
GEN_TIMEOUT_S = float(os.getenv("GEN_TIMEOUT_S", "60"))

# Tool router (LLM) timeout in seconds
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "10"))

# Prebuffer size (characters) for concurrent executor before tool decision
PREBUFFER_MAX_CHARS = int(os.getenv("PREBUFFER_MAX_CHARS", "1000"))


__all__ = [
    "GEN_TIMEOUT_S",
    "TOOL_TIMEOUT_S",
    "PREBUFFER_MAX_CHARS",
]


