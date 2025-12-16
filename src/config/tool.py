"""Tool classifier configuration.

Settings for the tool decision classifier model.
"""

from __future__ import annotations

import os

from ..utils.env import env_flag


# Tool language filter: skip tool call if user message is not mostly English
TOOL_LANGUAGE_FILTER = env_flag("TOOL_LANGUAGE_FILTER", True)

# Decision threshold for tool activation
TOOL_DECISION_THRESHOLD = float(os.getenv("TOOL_DECISION_THRESHOLD", "0.66"))

# Torch dynamo recompiles frequently with variable-length histories; keep eager by default
TOOL_COMPILE = env_flag("TOOL_COMPILE", False)

# Token limits for tool model
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1536"))
TOOL_MAX_LENGTH = int(os.getenv("TOOL_MAX_LENGTH", "1536"))

# Microbatching settings
TOOL_MICROBATCH_MAX_SIZE = int(os.getenv("TOOL_MICROBATCH_MAX_SIZE", "3"))
TOOL_MICROBATCH_MAX_DELAY_MS = float(os.getenv("TOOL_MICROBATCH_MAX_DELAY_MS", "10.0"))


__all__ = [
    "TOOL_LANGUAGE_FILTER",
    "TOOL_DECISION_THRESHOLD",
    "TOOL_COMPILE",
    "TOOL_HISTORY_TOKENS",
    "TOOL_MAX_LENGTH",
    "TOOL_MICROBATCH_MAX_SIZE",
    "TOOL_MICROBATCH_MAX_DELAY_MS",
]

