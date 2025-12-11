"""Token, history, and concurrency limits configuration."""

import os


CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5025"))  # 1650 persona + 3000 history + 350 user + 25 tool reply
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "150"))
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
CHAT_PROMPT_MAX_TOKENS = int(os.getenv("CHAT_PROMPT_MAX_TOKENS", "1650"))

# Personality validation
PERSONALITY_MAX_LEN = int(os.getenv("PERSONALITY_MAX_LEN", "20"))

# Personalities list limits
MAX_PERSONALITIES = int(os.getenv("MAX_PERSONALITIES", "50"))
MAX_SYNONYMS_PER_PERSONALITY = int(os.getenv("MAX_SYNONYMS_PER_PERSONALITY", "10"))

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
WS_MAX_MESSAGES_PER_WINDOW = int(os.getenv("WS_MAX_MESSAGES_PER_WINDOW", "25"))
WS_CANCEL_WINDOW_SECONDS = float(os.getenv(
    "WS_CANCEL_WINDOW_SECONDS",
    str(WS_MESSAGE_WINDOW_SECONDS),
))
WS_MAX_CANCELS_PER_WINDOW = int(os.getenv("WS_MAX_CANCELS_PER_WINDOW", str(WS_MAX_MESSAGES_PER_WINDOW)))

# Tool model history limit
TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "900"))  # Tool model context allocation

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = os.getenv("EXACT_TOKEN_TRIM", "1") == "1"

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

# Memory tuning constants for max_num_seqs calculation
MAX_NUM_SEQS_BASELINE = int(os.getenv("MAX_NUM_SEQS_BASELINE", "96"))
MAX_NUM_SEQS_MIN_FLOOR = int(os.getenv("MAX_NUM_SEQS_MIN_FLOOR", "32"))
MAX_NUM_SEQS_MEMORY_OPT_BASELINE = int(os.getenv("MAX_NUM_SEQS_MEMORY_OPT_BASELINE", "64"))
MAX_NUM_SEQS_MAX_RESOLVED = int(os.getenv("MAX_NUM_SEQS_MAX_RESOLVED", "128"))

# GPU size thresholds (GiB) for max_num_seqs scaling
MAX_NUM_SEQS_GPU_THRESHOLD_SMALL = float(os.getenv("MAX_NUM_SEQS_GPU_THRESHOLD_SMALL", "36"))
MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM = float(os.getenv("MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM", "48"))
MAX_NUM_SEQS_GPU_THRESHOLD_LARGE = float(os.getenv("MAX_NUM_SEQS_GPU_THRESHOLD_LARGE", "72"))

# Baseline max_num_seqs values for different GPU sizes
MAX_NUM_SEQS_BASELINE_SMALL = int(os.getenv("MAX_NUM_SEQS_BASELINE_SMALL", "48"))
MAX_NUM_SEQS_BASELINE_MEDIUM = int(os.getenv("MAX_NUM_SEQS_BASELINE_MEDIUM", "56"))
MAX_NUM_SEQS_BASELINE_LARGE = int(os.getenv("MAX_NUM_SEQS_BASELINE_LARGE", "72"))
MAX_NUM_SEQS_BASELINE_XLARGE = int(os.getenv("MAX_NUM_SEQS_BASELINE_XLARGE", "112"))

# Allocation ratio bounds for max_num_seqs calculation
MAX_NUM_SEQS_ALLOCATION_RATIO_MIN = float(os.getenv("MAX_NUM_SEQS_ALLOCATION_RATIO_MIN", "0.4"))
MAX_NUM_SEQS_ALLOCATION_RATIO_MAX = float(os.getenv("MAX_NUM_SEQS_ALLOCATION_RATIO_MAX", "0.95"))
MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR = float(os.getenv("MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR", "0.85"))

# Batching limits scaling constants
BATCH_SCALE_MIN_RATIO = float(os.getenv("BATCH_SCALE_MIN_RATIO", "0.1"))
BATCH_SCALE_MIN_TOKENS = int(os.getenv("BATCH_SCALE_MIN_TOKENS", "64"))
BATCH_SCALE_MIN_SEQS = int(os.getenv("BATCH_SCALE_MIN_SEQS", "4"))

# GPU fraction cap for batching: matches CHAT_GPU_FRAC based on deployment mode
# When both chat and tool are deployed: default 0.70
# When only chat is deployed: default 0.90
# This prevents pushing memory allocation beyond the configured GPU fraction
_env_cap = os.getenv("BATCH_SCALE_GPU_FRAC_CAP")
if _env_cap is not None:
    BATCH_SCALE_GPU_FRAC_CAP = float(_env_cap)
else:
    # Replicate CHAT_GPU_FRAC logic to avoid circular import with env.py
    _deploy_models = (os.getenv("DEPLOY_MODELS", "both") or "both").lower()
    _deploy_chat = _deploy_models in ("both", "chat")
    _deploy_tool = _deploy_models in ("both", "tool")
    if _deploy_chat and _deploy_tool:
        BATCH_SCALE_GPU_FRAC_CAP = float(os.getenv("CHAT_GPU_FRAC", "0.70"))
    else:
        BATCH_SCALE_GPU_FRAC_CAP = float(os.getenv("CHAT_GPU_FRAC", "0.90"))

__all__ = [
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
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
    "PERSONALITY_MAX_LEN",
    "MAX_PERSONALITIES",
    "MAX_SYNONYMS_PER_PERSONALITY",
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
    "MAX_CONCURRENT_CONNECTIONS",
    "SCREEN_PREFIX_MAX_CHARS",
    # Memory tuning constants
    "MAX_NUM_SEQS_BASELINE",
    "MAX_NUM_SEQS_MIN_FLOOR",
    "MAX_NUM_SEQS_MEMORY_OPT_BASELINE",
    "MAX_NUM_SEQS_MAX_RESOLVED",
    "MAX_NUM_SEQS_GPU_THRESHOLD_SMALL",
    "MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM",
    "MAX_NUM_SEQS_GPU_THRESHOLD_LARGE",
    "MAX_NUM_SEQS_BASELINE_SMALL",
    "MAX_NUM_SEQS_BASELINE_MEDIUM",
    "MAX_NUM_SEQS_BASELINE_LARGE",
    "MAX_NUM_SEQS_BASELINE_XLARGE",
    "MAX_NUM_SEQS_ALLOCATION_RATIO_MIN",
    "MAX_NUM_SEQS_ALLOCATION_RATIO_MAX",
    "MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR",
    "BATCH_SCALE_MIN_RATIO",
    "BATCH_SCALE_MIN_TOKENS",
    "BATCH_SCALE_MIN_SEQS",
    "BATCH_SCALE_GPU_FRAC_CAP",
]