"""HTTP surface configuration values."""

from __future__ import annotations

import os

DEFAULT_HEALTH_ALLOWED_CIDRS = "127.0.0.1/32,::1/128"
HEALTH_ALLOWED_CIDRS = os.getenv("HEALTH_ALLOWED_CIDRS", DEFAULT_HEALTH_ALLOWED_CIDRS)

__all__ = [
    "DEFAULT_HEALTH_ALLOWED_CIDRS",
    "HEALTH_ALLOWED_CIDRS",
]
