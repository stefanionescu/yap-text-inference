"""Default constants and persona variants for test utilities.

This module contains hardcoded defaults for benchmarks, personality tests,
sampling parameters, and persona variants. These values are used when no
environment override is provided and serve as the baseline configuration
for all test scripts.
"""

from __future__ import annotations

from tests.prompts.base import FEMALE_PROMPT, MALE_PROMPT
from tests.prompts.detailed import (
    ANNA_FLIRTY,
    ANNA_RELIGIOUS,
    ANNA_SPIRITUAL,
    MARK_SAVAGE,
    MARK_DELULU,
)

# Default personalities for tool phrase matching
# Keys are personality names, values are lists of synonyms
DEFAULT_PERSONALITIES: dict[str, list[str]] = {
    "friendly": ["generic", "normal"],
    "flirty": ["horny", "sexy", "turned on"],
    "religious": ["priest", "pious"],
    "delulu": ["delooloo", "de loo loo", "delusional"],
    "savage": ["no cap", "unfiltered"],
    "spiritual": ["zen", "new age", "mystic"],
}

WARMUP_FALLBACK_MESSAGE = "hey there! how are you today?"
BENCHMARK_FALLBACK_MESSAGE = "who was Columbus?"

BENCHMARK_DEFAULT_REQUESTS = 16
BENCHMARK_DEFAULT_CONCURRENCY = 8
BENCHMARK_DEFAULT_TIMEOUT_SEC = 120.0

# Burst mode defaults
BENCHMARK_BURST_MODE_DEFAULT = "instant"  # "instant" or "windowed"
BENCHMARK_BURST_SIZE_DEFAULT = 3  # transactions per window
BENCHMARK_WINDOW_DURATION_DEFAULT = 0.5  # seconds per window

PERSONALITY_SWITCH_MIN = 1
PERSONALITY_SWITCH_MAX = 10
PERSONALITY_SWITCH_DEFAULT = 4
PERSONALITY_SWITCH_DELAY_SECONDS = 10
PERSONALITY_REPLIES_PER_SWITCH = 2

PERSONA_VARIANTS = [
    ("female", "flirty", FEMALE_PROMPT),
    ("male", "flirty", MALE_PROMPT),
]

# Personality test variants: alternating Anna/Mark with different personalities
# Pattern: Anna flirty -> Mark savage -> Anna religious -> Mark delulu -> Anna spiritual
PERSONALITY_PERSONA_VARIANTS = [
    ("female", "flirty", ANNA_FLIRTY),
    ("male", "savage", MARK_SAVAGE),
    ("female", "religious", ANNA_RELIGIOUS),
    ("male", "delulu", MARK_DELULU),
    ("female", "spiritual", ANNA_SPIRITUAL),
]

# Sampling defaults mirrored from src.config.sampling for CLI usage
CHAT_TEMPERATURE_DEFAULT = 0.9
CHAT_TOP_P_DEFAULT = 0.90
CHAT_TOP_K_DEFAULT = 40
CHAT_REPETITION_PENALTY_DEFAULT = 1.05
CHAT_PRESENCE_PENALTY_DEFAULT = 0.20
CHAT_FREQUENCY_PENALTY_DEFAULT = 0.20

# Connection lifecycle sanity defaults
CONNECTION_NORMAL_WAIT_DEFAULT = 3.0
CONNECTION_IDLE_EXPECT_DEFAULT = 150.0
CONNECTION_IDLE_GRACE_DEFAULT = 15.0

# WebSocket defaults
DEFAULT_WS_PATH = "/ws"

# Persona registry defaults
PERSONA_MODULE = "tests.prompts.detailed"
DEFAULT_PERSONA_NAME = "anna_flirty"

__all__ = [
    "DEFAULT_PERSONALITIES",
    "WARMUP_FALLBACK_MESSAGE",
    "BENCHMARK_FALLBACK_MESSAGE",
    "BENCHMARK_DEFAULT_REQUESTS",
    "BENCHMARK_DEFAULT_CONCURRENCY",
    "BENCHMARK_DEFAULT_TIMEOUT_SEC",
    "BENCHMARK_BURST_MODE_DEFAULT",
    "BENCHMARK_BURST_SIZE_DEFAULT",
    "BENCHMARK_WINDOW_DURATION_DEFAULT",
    "PERSONALITY_SWITCH_MIN",
    "PERSONALITY_SWITCH_MAX",
    "PERSONALITY_SWITCH_DEFAULT",
    "PERSONALITY_SWITCH_DELAY_SECONDS",
    "PERSONALITY_REPLIES_PER_SWITCH",
    "PERSONA_VARIANTS",
    "PERSONALITY_PERSONA_VARIANTS",
    "CHAT_TEMPERATURE_DEFAULT",
    "CHAT_TOP_P_DEFAULT",
    "CHAT_TOP_K_DEFAULT",
    "CHAT_REPETITION_PENALTY_DEFAULT",
    "CHAT_PRESENCE_PENALTY_DEFAULT",
    "CHAT_FREQUENCY_PENALTY_DEFAULT",
    "CONNECTION_NORMAL_WAIT_DEFAULT",
    "CONNECTION_IDLE_EXPECT_DEFAULT",
    "CONNECTION_IDLE_GRACE_DEFAULT",
    "DEFAULT_WS_PATH",
    "PERSONA_MODULE",
    "DEFAULT_PERSONA_NAME",
]
