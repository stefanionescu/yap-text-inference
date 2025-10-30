"""Sampling defaults for chat and tool models.

All values may be overridden via environment variables when applicable.
Stop sequences are centralized here for consistency.
"""

import os


# --- Chat sampling ---
CHAT_TEMPERATURE = float(os.getenv("CHAT_TEMPERATURE", "0.55"))
CHAT_TOP_P = float(os.getenv("CHAT_TOP_P", "0.90"))
CHAT_TOP_K = int(os.getenv("CHAT_TOP_K", "60"))
CHAT_MIN_P = float(os.getenv("CHAT_MIN_P", "0.05"))
CHAT_REPEAT_PENALTY = float(os.getenv("CHAT_REPEAT_PENALTY", "1.10"))

# Extra STOP sequences used by chat model
CHAT_STOP = [
    " |",
    "  |",
    "<|im_end|>",
    "|im_end|>",
    " ‍♀️",
    " ‍♂️",
    "<|end|>",
    "</s>",
]


# --- Tool sampling ---
TOOL_TEMPERATURE = float(os.getenv("TOOL_TEMPERATURE", "0.05"))
TOOL_TOP_P = float(os.getenv("TOOL_TOP_P", "1.0"))
TOOL_TOP_K = int(os.getenv("TOOL_TOP_K", "1"))
TOOL_STOP = ["\n", "</s>"]


__all__ = [
    "CHAT_TEMPERATURE",
    "CHAT_TOP_P",
    "CHAT_TOP_K",
    "CHAT_MIN_P",
    "CHAT_REPEAT_PENALTY",
    "CHAT_STOP",
    "TOOL_TEMPERATURE",
    "TOOL_TOP_P",
    "TOOL_TOP_K",
    "TOOL_STOP",
]


