"""Token, history, and concurrency limits configuration.

This module defines the various limits that control resource usage and
protect against abuse. Limits are organized into categories:

Context Limits:
    - CHAT_MAX_LEN: Maximum input context length (tokens)
    - CHAT_MAX_OUT: Maximum generation length (tokens)
    - HISTORY_MAX_TOKENS: Threshold that triggers history trimming (tokens)
    - TRIMMED_HISTORY_LENGTH: Target length after trimming (tokens)
    - USER_UTT_MAX_TOKENS: Maximum user utterance (tokens)
    - CHAT_PROMPT_MAX_TOKENS: Maximum persona prompt (tokens)

Rate Limits:
    - WS_MAX_MESSAGES_PER_WINDOW: Message rate limit
    - WS_MAX_CANCELS_PER_WINDOW: Cancel rate limit

All values can be overridden via environment variables.
"""

import os
from ..helpers.env import env_flag
from ..helpers.resolvers import resolve_batch_scale_gpu_frac_cap

# ============================================================================
# Context Window Limits
# ============================================================================
# These define the maximum token budget for different components.
# Total budget breakdown: 1500 persona + 3000 history + 500 user + 25 buffer

CHAT_MAX_LEN = int(os.getenv("CHAT_MAX_LEN", "5025"))  # Total context window
CHAT_MAX_OUT = int(os.getenv("CHAT_MAX_OUT", "150"))  # Max generation tokens
PROMPT_SANITIZE_MAX_CHARS = int(os.getenv("PROMPT_SANITIZE_MAX_CHARS", str(CHAT_MAX_LEN * 6)))

# Max tokens allowed for incoming prompts (provided by clients)
CHAT_PROMPT_MAX_TOKENS = int(os.getenv("CHAT_PROMPT_MAX_TOKENS", "1500"))

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5-15ms
STREAM_FLUSH_MS = float(os.getenv("STREAM_FLUSH_MS", "0"))

# History and user limits (token counts from active tokenizer path)
# HISTORY_MAX_TOKENS: threshold that triggers trimming
# TRIMMED_HISTORY_LENGTH: target length after trimming (must be < HISTORY_MAX_TOKENS)
HISTORY_MAX_TOKENS = int(os.getenv("HISTORY_MAX_TOKENS", "3000"))
TRIMMED_HISTORY_LENGTH = int(os.getenv("TRIMMED_HISTORY_LENGTH", "2000"))
USER_UTT_MAX_TOKENS = int(os.getenv("USER_UTT_MAX_TOKENS", "500"))

# WebSocket message/cancel rate limits (rolling window)
WS_MESSAGE_WINDOW_SECONDS = float(os.getenv("WS_MESSAGE_WINDOW_SECONDS", "60"))
WS_MAX_MESSAGES_PER_WINDOW = int(os.getenv("WS_MAX_MESSAGES_PER_WINDOW", "25"))
WS_CANCEL_WINDOW_SECONDS = float(
    os.getenv(
        "WS_CANCEL_WINDOW_SECONDS",
        str(WS_MESSAGE_WINDOW_SECONDS),
    )
)
WS_MAX_CANCELS_PER_WINDOW = int(os.getenv("WS_MAX_CANCELS_PER_WINDOW", str(WS_MAX_MESSAGES_PER_WINDOW)))

# Exact tokenization for trimming (uses Hugging Face tokenizer); fast on CPU
EXACT_TOKEN_TRIM = env_flag("EXACT_TOKEN_TRIM", True)

# Maximum concurrent WebSocket connections
# Validated at runtime by helpers/validation.py
_max_concurrent_raw = os.getenv("MAX_CONCURRENT_CONNECTIONS")
MAX_CONCURRENT_CONNECTIONS: int | None = int(_max_concurrent_raw) if _max_concurrent_raw else None

# GPU fraction cap for batching: matches CHAT_GPU_FRAC based on deployment mode.
# Prevents pushing memory allocation beyond the configured GPU fraction.
_deploy_models = (os.getenv("DEPLOY_MODE", "both") or "both").lower()
_deploy_chat = _deploy_models in ("both", "chat")
_deploy_tool = _deploy_models in ("both", "tool")
BATCH_SCALE_GPU_FRAC_CAP = resolve_batch_scale_gpu_frac_cap(_deploy_chat, _deploy_tool)

# ============================================================================
# Sampling Clamps
# ============================================================================
CHAT_TEMPERATURE_MIN = 0.0
CHAT_TEMPERATURE_MAX = 1.2
CHAT_TOP_P_MIN = 0.6
CHAT_TOP_P_MAX = 1.0
CHAT_TOP_K_MIN = 0
CHAT_TOP_K_MAX = 60
CHAT_MIN_P_MIN = 0.0
CHAT_MIN_P_MAX = 0.20
CHAT_REPETITION_PENALTY_MIN = 1.0
CHAT_REPETITION_PENALTY_MAX = 1.3
CHAT_PRESENCE_PENALTY_MIN = 0.0
CHAT_PRESENCE_PENALTY_MAX = 0.5
CHAT_FREQUENCY_PENALTY_MIN = 0.0
CHAT_FREQUENCY_PENALTY_MAX = 0.5

# Personality validation
PERSONALITY_MAX_LEN = 20

# Screen prefix validation
SCREEN_PREFIX_MAX_CHARS = 30

# ============================================================================
# Memory Tuning Constants
# ============================================================================
MAX_NUM_SEQS_BASELINE = 96
MAX_NUM_SEQS_MIN_FLOOR = 32
MAX_NUM_SEQS_MEMORY_OPT_BASELINE = 64
MAX_NUM_SEQS_MAX_RESOLVED = 128
MAX_NUM_SEQS_GPU_THRESHOLD_SMALL = 36.0
MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM = 48.0
MAX_NUM_SEQS_GPU_THRESHOLD_LARGE = 72.0
MAX_NUM_SEQS_BASELINE_SMALL = 48
MAX_NUM_SEQS_BASELINE_MEDIUM = 56
MAX_NUM_SEQS_BASELINE_LARGE = 72
MAX_NUM_SEQS_BASELINE_XLARGE = 112
MAX_NUM_SEQS_ALLOCATION_RATIO_MIN = 0.4
MAX_NUM_SEQS_ALLOCATION_RATIO_MAX = 0.95
MAX_NUM_SEQS_ALLOCATION_RATIO_DIVISOR = 0.85
BATCH_SCALE_MIN_RATIO = 0.1
BATCH_SCALE_MIN_TOKENS = 64
BATCH_SCALE_MIN_SEQS = 4

GPU_BASELINE_TIERS: list[tuple[float, int]] = [
    (MAX_NUM_SEQS_GPU_THRESHOLD_SMALL, MAX_NUM_SEQS_BASELINE_SMALL),
    (MAX_NUM_SEQS_GPU_THRESHOLD_MEDIUM, MAX_NUM_SEQS_BASELINE_MEDIUM),
    (MAX_NUM_SEQS_GPU_THRESHOLD_LARGE, MAX_NUM_SEQS_BASELINE_LARGE),
]

# Memory optimization
MEMORY_OPT_GPU_FRAC_CAP = 0.85

# MoE calibration
MOE_CALIBRATION_SAMPLES_LIMIT = 32

# Download retry
DOWNLOAD_MAX_RETRIES = 3
DOWNLOAD_BACKOFF_MAX_SECONDS = 5

__all__ = [
    "CHAT_MAX_LEN",
    "CHAT_MAX_OUT",
    "PROMPT_SANITIZE_MAX_CHARS",
    "CHAT_PROMPT_MAX_TOKENS",
    "STREAM_FLUSH_MS",
    "HISTORY_MAX_TOKENS",
    "TRIMMED_HISTORY_LENGTH",
    "USER_UTT_MAX_TOKENS",
    "WS_MESSAGE_WINDOW_SECONDS",
    "WS_MAX_MESSAGES_PER_WINDOW",
    "WS_CANCEL_WINDOW_SECONDS",
    "WS_MAX_CANCELS_PER_WINDOW",
    "EXACT_TOKEN_TRIM",
    "MAX_CONCURRENT_CONNECTIONS",
    "BATCH_SCALE_GPU_FRAC_CAP",
    # Sampling clamps
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
    # Personality / screen prefix
    "PERSONALITY_MAX_LEN",
    "SCREEN_PREFIX_MAX_CHARS",
    # Memory tuning
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
    "GPU_BASELINE_TIERS",
    "MEMORY_OPT_GPU_FRAC_CAP",
    "MOE_CALIBRATION_SAMPLES_LIMIT",
    "DOWNLOAD_MAX_RETRIES",
    "DOWNLOAD_BACKOFF_MAX_SECONDS",
]
