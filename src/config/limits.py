"""Token, history, and concurrency limits configuration."""

import os


CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5160"))  # 1800 persona + 3000 history + 350 user + 10 tool reply
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "150"))
TOOL_MAX_OUT = int(os.getenv("TOOL_MAX_OUT", "25"))
TOOL_MAX_LEN = int(os.getenv("TOOL_MAX_LEN", "3000"))  # 1450 system + 350 user + 1200 history
PROMPT_SANITIZE_MAX_CHARS = int(os.getenv("PROMPT_SANITIZE_MAX_CHARS", str(CHAT_MAX_LEN * 6)))

# Chat sampling override limits (optional client-provided values)
CHAT_TEMPERATURE_MIN = float(os.getenv("CHAT_TEMPERATURE_MIN", "0"))
CHAT_TEMPERATURE_MAX = float(os.getenv("CHAT_TEMPERATURE_MAX", "1.2"))
CHAT_TOP_P_MIN = float(os.getenv("CHAT_TOP_P_MIN", "0.6"))
CHAT_TOP_P_MAX = float(os.getenv("CHAT_TOP_P_MAX", "1.0"))
CHAT_TOP_K_MIN = int(os.getenv("CHAT_TOP_K_MIN", "0"))
CHAT_TOP_K_MAX = int(os.getenv("CHAT_TOP_K_MAX", "60"))
CHAT_MIN_P_MIN = float(os.getenv("CHAT_MIN_P_MIN", "0.0"))
CHAT_MIN_P_MAX = float(os.getenv("CHAT_MIN_P_MAX", "0.20"))
CHAT_REPETITION_PENALTY_MIN = float(os.getenv("CHAT_REPETITION_PENALTY_MIN", "1.0"))
CHAT_REPETITION_PENALTY_MAX = float(os.getenv("CHAT_REPETITION_PENALTY_MAX", "1.3"))
CHAT_PRESENCE_PENALTY_MIN = float(os.getenv("CHAT_PRESENCE_PENALTY_MIN", "0.0"))
CHAT_PRESENCE_PENALTY_MAX = float(os.getenv("CHAT_PRESENCE_PENALTY_MAX", "0.5"))
CHAT_FREQUENCY_PENALTY_MIN = float(os.getenv("CHAT_FREQUENCY_PENALTY_MIN", "0.0"))
CHAT_FREQUENCY_PENALTY_MAX = float(os.getenv("CHAT_FREQUENCY_PENALTY_MAX", "0.5"))

# Max tokens allowed for incoming prompts (provided by clients)
CHAT_PROMPT_MAX_TOKENS = int(os.getenv("CHAT_PROMPT_MAX_TOKENS", "1800"))
TOOL_PROMPT_MAX_TOKENS = int(os.getenv("TOOL_PROMPT_MAX_TOKENS", "1450"))

# Personality validation
PERSONALITY_MAX_LEN = int(os.getenv("PERSONALITY_MAX_LEN", "20"))

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5–15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

# History and user limits (approximate tokens)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "3000"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "350"))

# Persona update pacing (rolling window)
CHAT_PROMPT_UPDATE_WINDOW_SECONDS = float(os.getenv("CHAT_PROMPT_UPDATE_WINDOW_SECONDS", "60"))
CHAT_PROMPT_UPDATE_MAX_PER_WINDOW = int(os.getenv("CHAT_PROMPT_UPDATE_MAX_PER_WINDOW", "4"))

# WebSocket message/cancel rate limits (rolling window)
WS_MESSAGE_WINDOW_SECONDS = float(os.getenv("WS_MESSAGE_WINDOW_SECONDS", "60"))
WS_MAX_MESSAGES_PER_WINDOW = int(os.getenv("WS_MAX_MESSAGES_PER_WINDOW", "20"))
WS_CANCEL_WINDOW_SECONDS = float(os.getenv(
    "WS_CANCEL_WINDOW_SECONDS",
    str(WS_MESSAGE_WINDOW_SECONDS),
))
WS_MAX_CANCELS_PER_WINDOW = int(os.getenv("WS_MAX_CANCELS_PER_WINDOW", str(WS_MAX_MESSAGES_PER_WINDOW)))

# Tool model history limit
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1200"))  # Tool model context allocation

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"

# Concurrent toolcall mode: if True, run chat and tool models concurrently (default: True)
CONCURRENT_MODEL_CALL = os.getenv("CONCURRENT_MODEL_CALL", "1") == "1"

# Maximum concurrent WebSocket connections (must be provided explicitly)
_max_concurrent_raw = os.getenv("MAX_CONCURRENT_CONNECTIONS")
if _max_concurrent_raw is None:
    raise RuntimeError(
        "MAX_CONCURRENT_CONNECTIONS environment variable is required. "
        "Set it before starting the server."
    )
try:
    MAX_CONCURRENT_CONNECTIONS = int(_max_concurrent_raw)
except ValueError as exc:
    raise ValueError(
        f"MAX_CONCURRENT_CONNECTIONS must be an integer, got '{_max_concurrent_raw}'."
    ) from exc

# Screen prefix validation
SCREEN_PREFIX_MAX_CHARS = int(os.getenv("SCREEN_PREFIX_MAX_CHARS", "30"))

__all__ = [
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "TOOL_MAX_OUT",
    "TOOL_MAX_LEN",
    "PROMPT_SANITIZE_MAX_CHARS",
    "CHAT_TEMPERATURE_MIN",
    "CHAT_TEMPERATURE_MAX",
    "CHAT_TOP_P_MIN",
    "CHAT_TOP_P_MAX",
    "CHAT_TOP_K_MIN",
    "CHAT_TOP_K_MAX",
    "CHAT_MIN_P_MIN",
    "CHAT_MIN_P_MAX",
    "CHAT_REPETITION_PENALTY_MIN",
    "CHAT_REPETITION_PENALTY_MAX",
    "CHAT_PRESENCE_PENALTY_MIN",
    "CHAT_PRESENCE_PENALTY_MAX",
    "CHAT_FREQUENCY_PENALTY_MIN",
    "CHAT_FREQUENCY_PENALTY_MAX",
    "CHAT_PROMPT_MAX_TOKENS",
    "TOOL_PROMPT_MAX_TOKENS",
    "PERSONALITY_MAX_LEN",
    "STREAM_FLUSH_MS",
    "HISTORY_MAX_TOKENS",
    "USER_UTT_MAX_TOKENS",
    "CHAT_PROMPT_UPDATE_WINDOW_SECONDS",
    "CHAT_PROMPT_UPDATE_MAX_PER_WINDOW",
    "WS_MESSAGE_WINDOW_SECONDS",
    "WS_MAX_MESSAGES_PER_WINDOW",
    "WS_CANCEL_WINDOW_SECONDS",
    "WS_MAX_CANCELS_PER_WINDOW",
    "TOOL_HISTORY_TOKENS",
    "EXACT_TOKEN_TRIM",
    "CONCURRENT_MODEL_CALL",
    "MAX_CONCURRENT_CONNECTIONS",
    "SCREEN_PREFIX_MAX_CHARS",
]