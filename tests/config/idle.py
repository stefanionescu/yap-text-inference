"""Idle test configuration values.

Environment overrides for the idle timeout and connection lifecycle test harness.
Falls back to repo defaults when unset. Idle expectation uses WS_IDLE_TIMEOUT_S
if provided to ensure the watchdog test aligns with the deployment.
"""

from __future__ import annotations

import os

from tests.helpers.env import get_float_env

from .defaults import IDLE_GRACE_DEFAULT, IDLE_EXPECT_DEFAULT, IDLE_NORMAL_WAIT_DEFAULT

# Resolve idle expect fallback: prefer WS_IDLE_TIMEOUT_S if set, else use default
_ws_idle_raw = os.getenv("WS_IDLE_TIMEOUT_S")
_idle_expect_fallback = (
    float(_ws_idle_raw)
    if _ws_idle_raw is not None and _ws_idle_raw.strip()
    else IDLE_EXPECT_DEFAULT
)

IDLE_NORMAL_WAIT_SECONDS = get_float_env(
    "IDLE_NORMAL_WAIT_SECONDS",
    IDLE_NORMAL_WAIT_DEFAULT,
)

IDLE_EXPECT_SECONDS = get_float_env(
    "IDLE_EXPECT_SECONDS",
    _idle_expect_fallback,
)

IDLE_GRACE_SECONDS = get_float_env(
    "IDLE_GRACE_SECONDS",
    IDLE_GRACE_DEFAULT,
)


__all__ = [
    "IDLE_NORMAL_WAIT_SECONDS",
    "IDLE_EXPECT_SECONDS",
    "IDLE_GRACE_SECONDS",
]
