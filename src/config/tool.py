"""Tool classifier configuration.

This module configures the screenshot intent classifier - a lightweight
PyTorch model that determines whether the user is asking for a screenshot.

The classifier runs independently of the main chat engine and is optimized
for low latency. It uses:
- Micro-batching to amortize GPU overhead
- Left-truncation for long inputs
- Language filtering to skip non-English messages

Decision Flow:
    1. User sends a message
    2. Phrase filter checks for known patterns (typos, exact matches)
    3. Language filter checks if message is English
    4. Classifier runs inference with user + history context
    5. If probability >= threshold, return take_screenshot tool call

Environment Variables:
    TOOL_LANGUAGE_FILTER: Skip classifier for non-English messages
    TOOL_DECISION_THRESHOLD: Probability threshold for screenshot detection
    TOOL_COMPILE: Enable torch.compile optimization
    TOOL_HISTORY_TOKENS: Max tokens of history context
    TOOL_MAX_LENGTH: Max total input length
    TOOL_MICROBATCH_MAX_SIZE: Max requests per batch
    TOOL_MICROBATCH_MAX_DELAY_MS: Max wait time for batch fill
"""

from __future__ import annotations

import os

from ..helpers.env import env_flag

# ============================================================================
# Language Filtering
# ============================================================================
# Skip classifier for non-English messages to avoid false positives.
# Uses the lingua library for accurate detection, even on short text.

TOOL_LANGUAGE_FILTER = env_flag("TOOL_LANGUAGE_FILTER", True)

# ============================================================================
# Decision Threshold
# ============================================================================
# Classifier outputs a probability for "should take screenshot".
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
# Classifier uses recent conversation history for context. These limits
# prevent OOM and keep latency low.

TOOL_HISTORY_TOKENS = int(os.getenv("TOOL_HISTORY_TOKENS", "1536"))  # History budget
TOOL_MAX_LENGTH = int(os.getenv("TOOL_MAX_LENGTH", "1536"))  # Total input budget

# ============================================================================
# Micro-batching
# ============================================================================
# Batch concurrent requests to improve GPU utilization. The executor waits
# up to max_delay_ms to fill a batch of max_size before running inference.

TOOL_MICROBATCH_MAX_SIZE = int(os.getenv("TOOL_MICROBATCH_MAX_SIZE", "3"))
TOOL_MICROBATCH_MAX_DELAY_MS = float(os.getenv("TOOL_MICROBATCH_MAX_DELAY_MS", "10.0"))

# ============================================================================
# Classifier Runtime Constants
# ============================================================================
# Internal constants for classifier adapter behavior.

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
    "TOOL_LANGUAGE_FILTER",
    "TOOL_DECISION_THRESHOLD",
    "TOOL_COMPILE",
    "TOOL_HISTORY_TOKENS",
    "TOOL_MAX_LENGTH",
    "TOOL_MICROBATCH_MAX_SIZE",
    "TOOL_MICROBATCH_MAX_DELAY_MS",
    "TOOL_MIN_TIMEOUT_S",
    "TOOL_MIN_GPU_FRAC",
    "TOOL_MAX_GPU_FRAC",
    "TOOL_POSITIVE_RESULT",
    "TOOL_NEGATIVE_RESULT",
    "TOOL_POSITIVE_LABEL_INDEX",
]
