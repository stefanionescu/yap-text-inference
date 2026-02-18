"""Tool model configuration.

This module configures the screenshot intent tool model - a lightweight
PyTorch model that determines whether the user is asking for a screenshot.

The tool model runs independently of the main chat engine and is optimized
for low latency. It uses:
- Micro-batching to amortize GPU overhead
- Left-truncation for long inputs

Decision Flow:
    1. User sends a message
    2. Tool model runs inference with user + history context
    3. If probability >= threshold, return take_screenshot tool call

Environment Variables:
    TOOL_DECISION_THRESHOLD: Probability threshold for screenshot detection
    TOOL_COMPILE: Enable torch.compile optimization
    TOOL_HISTORY_TOKENS: Max tokens of history context
    TOOL_MAX_LENGTH: Max total input length

Note: Micro-batching parameters (batch size, delay) are hardcoded per model
in src.config.models.TOOL_MODEL_BATCH_CONFIG.
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag

# ============================================================================
# Decision Threshold
# ============================================================================
# Tool model outputs a probability for "should take screenshot".
# Values >= threshold trigger the tool call. 0.66 balances precision/recall.

TOOL_DECISION_THRESHOLD = float(os.getenv("TOOL_DECISION_THRESHOLD", "0.66"))

# ============================================================================
# Model Optimization
# ============================================================================
# torch.compile can improve throughput but has warmup overhead and may
# cause recompilations with variable input shapes. Disabled by default.

TOOL_COMPILE = env_flag("TOOL_COMPILE", False)

# ============================================================================
# Token Limits
# ============================================================================
# Tool model uses recent conversation history for context. These limits
# prevent OOM and keep latency low.

_tool_history_tokens_raw = os.getenv("TOOL_HISTORY_TOKENS")
TOOL_HISTORY_TOKENS_CONFIGURED = _tool_history_tokens_raw is not None
TOOL_HISTORY_TOKENS = int(_tool_history_tokens_raw) if _tool_history_tokens_raw is not None else 1536

_tool_max_length_raw = os.getenv("TOOL_MAX_LENGTH")
TOOL_MAX_LENGTH_CONFIGURED = _tool_max_length_raw is not None
TOOL_MAX_LENGTH = int(_tool_max_length_raw) if _tool_max_length_raw is not None else 1536

# ============================================================================
# Per-model micro-batching
# ============================================================================
# Hardcoded batch parameters per tool model.  Keyed by model ID.
# batch_max_size  – max requests per micro-batch
# batch_max_delay_ms – max wait time (ms) to fill a batch

TOOL_MODEL_BATCH_CONFIG: dict[str, dict[str, int | float]] = {
    "yapwithai/yap-longformer-screenshot-intent": {"batch_max_size": 3, "batch_max_delay_ms": 10.0, "max_length": 1536},
    "yapwithai/yap-modernbert-screenshot-intent": {"batch_max_size": 5, "batch_max_delay_ms": 15.0, "max_length": 512},
    "yapwithai/yap-distilroberta-screenshot-intent": {
        "batch_max_size": 10,
        "batch_max_delay_ms": 25.0,
        "max_length": 512,
    },
}

# ============================================================================
# Tool Runtime Constants
# ============================================================================
# Internal constants for tool adapter behavior.

# Minimum request timeout to prevent immediate failures
TOOL_MIN_TIMEOUT_S = 0.1

# GPU memory fraction bounds (safety limits for TOOL_GPU_FRAC)
TOOL_MIN_GPU_FRAC = 0.01
TOOL_MAX_GPU_FRAC = 0.90

# Classification output templates
TOOL_POSITIVE_RESULT: list[dict] = [{"name": "take_screenshot"}]
TOOL_NEGATIVE_RESULT: list[dict] = []

# Binary classification label index for positive class
TOOL_POSITIVE_LABEL_INDEX = 1


__all__ = [
    "TOOL_DECISION_THRESHOLD",
    "TOOL_COMPILE",
    "TOOL_HISTORY_TOKENS",
    "TOOL_HISTORY_TOKENS_CONFIGURED",
    "TOOL_MAX_LENGTH",
    "TOOL_MAX_LENGTH_CONFIGURED",
    "TOOL_MIN_TIMEOUT_S",
    "TOOL_MIN_GPU_FRAC",
    "TOOL_MAX_GPU_FRAC",
    "TOOL_POSITIVE_RESULT",
    "TOOL_NEGATIVE_RESULT",
    "TOOL_POSITIVE_LABEL_INDEX",
    "TOOL_MODEL_BATCH_CONFIG",
]
