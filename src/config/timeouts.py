"""Timeouts and buffering configuration.

Centralizes generation timeouts and executor buffering sizes.
Values are sourced from environment variables with sensible defaults.
"""

import os


# Chat/text generation hard timeout in seconds
GEN_TIMEOUT_S = float(os.getenv("GEN_TIMEOUT_S", "60"))

# Tool router (LLM) timeout in seconds
TOOL_TIMEOUT_S = float(os.getenv("TOOL_TIMEOUT_S", "10"))

# Tool hard timeout for concurrent/sequential decision in milliseconds
TOOL_HARD_TIMEOUT_MS = float(os.getenv("TOOL_HARD_TIMEOUT_MS", "500"))

# Prebuffer size (characters) for concurrent executor before tool decision
PREBUFFER_MAX_CHARS = int(os.getenv("PREBUFFER_MAX_CHARS", "1000"))


__all__ = [
    "GEN_TIMEOUT_S",
    "TOOL_TIMEOUT_S",
    "TOOL_HARD_TIMEOUT_MS",
    "PREBUFFER_MAX_CHARS",
]


