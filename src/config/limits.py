"""Token, history, and concurrency limits configuration.

This module defines the various limits that control resource usage and
protect against abuse. Limits are organized into categories:

Context Limits:
    - CHAT_MAX_LEN: Maximum input context length (tokens)
    - CHAT_MAX_OUT: Maximum generation length (tokens)
    - CHAT_HISTORY_MAX_TOKENS: Threshold that triggers history trimming (tokens)
    - TRIMMED_HISTORY_LENGTH: Target length after trimming (tokens)
    - USER_UTT_MAX_TOKENS: Maximum user utterance (tokens)
    - CHAT_PROMPT_MAX_TOKENS: Maximum persona prompt (tokens)

Most values can be overridden via environment variables.
"""

from .deploy import DEPLOY_CHAT, DEPLOY_TOOL
from ..helpers.resolvers import LimitValues, resolve_limit_values, resolve_batch_scale_gpu_frac_cap

# ============================================================================
# Context Window Limits
# ============================================================================
# These define the maximum token budget for different components.
# Total budget breakdown: 1500 persona + 3000 history + 500 user + 25 buffer

_LIMIT_VALUES: LimitValues = resolve_limit_values()

# Max tokens allowed for incoming prompts (provided by clients)
CHAT_PROMPT_MAX_TOKENS = int(_LIMIT_VALUES["CHAT_PROMPT_MAX_TOKENS"])

# History and user limits (token counts from active tokenizer path)
# CHAT_HISTORY_MAX_TOKENS: threshold that triggers trimming
CHAT_HISTORY_MAX_TOKENS = int(_LIMIT_VALUES["CHAT_HISTORY_MAX_TOKENS"])
USER_UTT_MAX_TOKENS = int(_LIMIT_VALUES["USER_UTT_MAX_TOKENS"])

# Percentage of CHAT_HISTORY_MAX_TOKENS to retain after trimming
HISTORY_RETENTION_PCT = int(_LIMIT_VALUES["HISTORY_RETENTION_PCT"])

CONTEXT_BUFFER = int(_LIMIT_VALUES["CONTEXT_BUFFER"])

CHAT_MAX_LEN = int(_LIMIT_VALUES["CHAT_MAX_LEN"])
CHAT_MAX_OUT = int(_LIMIT_VALUES["CHAT_MAX_OUT"])  # Max generation tokens

# TRIMMED_HISTORY_LENGTH: target length after trimming (must be < CHAT_HISTORY_MAX_TOKENS)
TRIMMED_HISTORY_LENGTH = int(_LIMIT_VALUES["TRIMMED_HISTORY_LENGTH"])

# Optional tiny coalescer: 0 = off; if you ever want to reduce packet spam set 5-15ms
STREAM_FLUSH_MS = float(_LIMIT_VALUES["STREAM_FLUSH_MS"])

# Maximum concurrent WebSocket connections
# Validated at runtime by helpers/validation.py
_max_concurrent_value = _LIMIT_VALUES["MAX_CONCURRENT_CONNECTIONS"]
MAX_CONCURRENT_CONNECTIONS: int | None = None if _max_concurrent_value is None else int(_max_concurrent_value)

# GPU fraction cap for batching: matches CHAT_GPU_FRAC based on deployment mode.
# Prevents pushing memory allocation beyond the configured GPU fraction.
BATCH_SCALE_GPU_FRAC_CAP = resolve_batch_scale_gpu_frac_cap(DEPLOY_CHAT, DEPLOY_TOOL)

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
    "CHAT_PROMPT_MAX_TOKENS",
    "STREAM_FLUSH_MS",
    "CHAT_HISTORY_MAX_TOKENS",
    "TRIMMED_HISTORY_LENGTH",
    "USER_UTT_MAX_TOKENS",
    "HISTORY_RETENTION_PCT",
    "CONTEXT_BUFFER",
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
