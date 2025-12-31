"""Connection test configuration values.

Resolves environment overrides for the connection lifecycle test harness,
falling back to repo defaults when unset. Idle expectation defaults to the
server's configured `WS_IDLE_TIMEOUT_S` if provided to ensure the watchdog
test aligns with the deployment.
"""

from __future__ import annotations

import os

from .defaults import (
    CONNECTION_IDLE_EXPECT_DEFAULT,
    CONNECTION_IDLE_GRACE_DEFAULT,
    CONNECTION_NORMAL_WAIT_DEFAULT,
)
from .env import get_float_env


def _resolve_idle_expect_default() -> float:
    candidate = os.getenv("WS_IDLE_TIMEOUT_S")
    if candidate is None:
        return CONNECTION_IDLE_EXPECT_DEFAULT
    try:
        return float(candidate)
    except ValueError:
        return CONNECTION_IDLE_EXPECT_DEFAULT


CONNECTION_NORMAL_WAIT_SECONDS = get_float_env(
    "CONNECTION_NORMAL_WAIT_SECONDS",
    CONNECTION_NORMAL_WAIT_DEFAULT,
)

CONNECTION_IDLE_EXPECT_SECONDS = get_float_env(
    "CONNECTION_IDLE_EXPECT_SECONDS",
    _resolve_idle_expect_default(),
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

