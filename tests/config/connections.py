"""Connection test configuration values.

Environment overrides for the connection lifecycle test harness. Falls back to
repo defaults when unset. Idle expectation uses WS_IDLE_TIMEOUT_S if provided
to ensure the watchdog test aligns with the deployment.
"""

from __future__ import annotations

import os

from tests.helpers.env import get_float_env

from .defaults import (
    CONNECTION_IDLE_EXPECT_DEFAULT,
    CONNECTION_IDLE_GRACE_DEFAULT,
    CONNECTION_NORMAL_WAIT_DEFAULT,
)


# Resolve idle expect fallback: prefer WS_IDLE_TIMEOUT_S if set, else use default
_ws_idle_raw = os.getenv("WS_IDLE_TIMEOUT_S")
_idle_expect_fallback = (
    float(_ws_idle_raw)
    if _ws_idle_raw is not None and _ws_idle_raw.strip()
    else CONNECTION_IDLE_EXPECT_DEFAULT
)

CONNECTION_NORMAL_WAIT_SECONDS = get_float_env(
    "CONNECTION_NORMAL_WAIT_SECONDS",
    CONNECTION_NORMAL_WAIT_DEFAULT,
)

CONNECTION_IDLE_EXPECT_SECONDS = get_float_env(
    "CONNECTION_IDLE_EXPECT_SECONDS",
    _idle_expect_fallback,
)

CONNECTION_IDLE_GRACE_SECONDS = get_float_env(
    "CONNECTION_IDLE_GRACE_SECONDS",
    CONNECTION_IDLE_GRACE_DEFAULT,
)


__all__ = [
    "CONNECTION_NORMAL_WAIT_SECONDS",
    "CONNECTION_IDLE_EXPECT_SECONDS",
    "CONNECTION_IDLE_GRACE_SECONDS",
]
