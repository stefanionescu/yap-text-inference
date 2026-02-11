"""Default constants and persona variants for test utilities.

This module contains hardcoded defaults for benchmarks, warmup/live tests,
sampling parameters, and persona variants. These values are used when no
environment override is provided and serve as the baseline configuration
for all test scripts.
"""

from __future__ import annotations

from tests.prompts.detailed import ANNA_FLIRTY, MARK_FLIRTY

WARMUP_FALLBACK_MESSAGE = "hey there! how are you today?"
BENCHMARK_FALLBACK_MESSAGE = "who was Columbus?"

BENCHMARK_DEFAULT_REQUESTS = 16
BENCHMARK_DEFAULT_CONCURRENCY = 8
BENCHMARK_DEFAULT_TIMEOUT_SEC = 120.0

# Burst mode defaults
BENCHMARK_BURST_MODE_DEFAULT = "instant"  # "instant" or "windowed"
BENCHMARK_BURST_SIZE_DEFAULT = 3  # transactions per window
BENCHMARK_WINDOW_DURATION_DEFAULT = 0.5  # seconds per window

# History benchmark defaults
HISTORY_BENCH_DEFAULT_REQUESTS = 8
HISTORY_BENCH_DEFAULT_CONCURRENCY = 4
HISTORY_BENCH_DEFAULT_TIMEOUT_SEC = 180.0

PERSONA_VARIANTS = [
    ("female", "flirty", ANNA_FLIRTY),
    ("male", "flirty", MARK_FLIRTY),
]

# Sampling defaults mirrored from src.config.sampling for CLI usage
CHAT_TEMPERATURE_DEFAULT = 0.9
CHAT_TOP_P_DEFAULT = 0.90
CHAT_TOP_K_DEFAULT = 40
CHAT_REPETITION_PENALTY_DEFAULT = 1.05
CHAT_PRESENCE_PENALTY_DEFAULT = 0.20
CHAT_FREQUENCY_PENALTY_DEFAULT = 0.20

# Idle test sanity defaults
IDLE_NORMAL_WAIT_DEFAULT = 3.0
IDLE_EXPECT_DEFAULT = 150.0
IDLE_GRACE_DEFAULT = 15.0

# Cancel test defaults
CANCEL_POST_WAIT_DEFAULT = 2.0  # Seconds to wait after cancel before recovery
CANCEL_RECV_TIMEOUT_DEFAULT = 30.0  # Timeout for each receive phase
CANCEL_NUM_CLIENTS_DEFAULT = 3  # Number of concurrent clients
CANCEL_DELAY_BEFORE_CANCEL_DEFAULT = 1.0  # Seconds to collect tokens before cancel
CANCEL_DRAIN_TIMEOUT_DEFAULT = 2.0  # Seconds to verify no spurious messages after cancel

# WebSocket defaults
DEFAULT_WS_PATH = "/ws"

# Progress bar display
PROGRESS_BAR_WIDTH = 30

# WebSocket queue limit (None = unlimited)
WS_MAX_QUEUE = None

# WebSocket idle close behavior
WS_IDLE_CLOSE_CODE = 4000
WS_IDLE_CLOSE_REASON = "idle_timeout"

# Persona registry defaults
PERSONA_MODULE = "tests.prompts.detailed"
DEFAULT_PERSONA_NAME = "anna_flirty"

__all__ = [
    "WARMUP_FALLBACK_MESSAGE",
    "BENCHMARK_FALLBACK_MESSAGE",
    "BENCHMARK_DEFAULT_REQUESTS",
    "BENCHMARK_DEFAULT_CONCURRENCY",
    "BENCHMARK_DEFAULT_TIMEOUT_SEC",
    "BENCHMARK_BURST_MODE_DEFAULT",
    "BENCHMARK_BURST_SIZE_DEFAULT",
    "BENCHMARK_WINDOW_DURATION_DEFAULT",
    "HISTORY_BENCH_DEFAULT_REQUESTS",
    "HISTORY_BENCH_DEFAULT_CONCURRENCY",
    "HISTORY_BENCH_DEFAULT_TIMEOUT_SEC",
    "PERSONA_VARIANTS",
    "CHAT_TEMPERATURE_DEFAULT",
    "CHAT_TOP_P_DEFAULT",
    "CHAT_TOP_K_DEFAULT",
    "CHAT_REPETITION_PENALTY_DEFAULT",
    "CHAT_PRESENCE_PENALTY_DEFAULT",
    "CHAT_FREQUENCY_PENALTY_DEFAULT",
    "IDLE_NORMAL_WAIT_DEFAULT",
    "IDLE_EXPECT_DEFAULT",
    "IDLE_GRACE_DEFAULT",
    "CANCEL_POST_WAIT_DEFAULT",
    "CANCEL_RECV_TIMEOUT_DEFAULT",
    "CANCEL_NUM_CLIENTS_DEFAULT",
    "CANCEL_DELAY_BEFORE_CANCEL_DEFAULT",
    "CANCEL_DRAIN_TIMEOUT_DEFAULT",
    "DEFAULT_WS_PATH",
    "PROGRESS_BAR_WIDTH",
    "WS_MAX_QUEUE",
    "WS_IDLE_CLOSE_CODE",
    "WS_IDLE_CLOSE_REASON",
    "PERSONA_MODULE",
    "DEFAULT_PERSONA_NAME",
]
