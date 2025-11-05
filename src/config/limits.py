"""Token, history, and concurrency limits configuration."""

import os


CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5160"))
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "200"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "10"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "3000"))  # 1450 system + 350 user + 1200 history

# Max tokens allowed for incoming prompts (provided by clients)
# Defaults per request: 1800 for both chat and tool prompts
CHAT_PROMPT_MAX_TOKENS = int(os.getenv("CHAT_PROMPT_MAX_TOKENS", "1800"))
TOOL_PROMPT_MAX_TOKENS = int(os.getenv("TOOL_PROMPT_MAX_TOKENS", "1800"))

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5–15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

# History and user limits (approximate tokens)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "2400"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "350"))

# Tool model specific limits
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1200"))  # Half of chat history for KV sharing
TOOL_SYSTEM_TOKENS = int(os.getenv("TOOL_SYSTEM_TOKENS", "1450"))  # System prompt + tool response

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"

# Concurrent toolcall mode: if True, run chat and tool models concurrently (default: True)
CONCURRENT_MODEL_CALL = os.getenv("CONCURRENT_MODEL_CALL", "1") == "1"

# Maximum concurrent WebSocket connections (deployment-aware and quantization-aware)
from .env import (
    DEPLOY_CHAT,
    DEPLOY_TOOL,
    QUANTIZATION,
    CHAT_QUANTIZATION,
    TOOL_QUANTIZATION,
)  # late import to avoid cycles


def _selected_quantization(is_chat: bool) -> str | None:
    if is_chat:
        return CHAT_QUANTIZATION or QUANTIZATION
    # Tool engine defaults to AWQ only when global QUANTIZATION=='awq'
    return TOOL_QUANTIZATION or ("awq" if QUANTIZATION == "awq" else None)


awq_enabled = (
    (DEPLOY_CHAT and _selected_quantization(True) == "awq")
    or (DEPLOY_TOOL and _selected_quantization(False) == "awq")
)

if awq_enabled:
    # Higher capacity when AWQ is used
    if DEPLOY_TOOL and not DEPLOY_CHAT:
        default_max = "64"  # tool-only (AWQ)
    elif DEPLOY_CHAT and not DEPLOY_TOOL:
        default_max = "40"  # chat-only (AWQ)
    else:
        default_max = "26"  # both models (AWQ)
else:
    # Default capacities for non-AWQ deployments
    if DEPLOY_TOOL and not DEPLOY_CHAT:
        default_max = "32"  # tool-only
    elif DEPLOY_CHAT and not DEPLOY_TOOL:
        default_max = "24"  # chat-only
    else:
        default_max = "16"  # both models

MAX_CONCURRENT_CONNECTIONS = int(os.getenv("MAX_CONCURRENT_CONNECTIONS", default_max))


__all__ = [
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "TOOL_MAX_OUT",
    "TOOL_MAX_LEN",
    "CHAT_PROMPT_MAX_TOKENS",
    "TOOL_PROMPT_MAX_TOKENS",
    "STREAM_FLUSH_MS",
    "HISTORY_MAX_TOKENS",
    "USER_UTT_MAX_TOKENS",
    "TOOL_HISTORY_TOKENS",
    "TOOL_SYSTEM_TOKENS",
    "EXACT_TOKEN_TRIM",
    "CONCURRENT_MODEL_CALL",
    "MAX_CONCURRENT_CONNECTIONS",
]


