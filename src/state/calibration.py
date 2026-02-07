"""Calibration-related dataclasses."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TotalLengthPolicy:
    """Represents how to compute minimum total sequence length for a model."""

    kind: str
    default_total: int
    len_env: str
    out_env: str

    def resolve(self, requested: int) -> int:
        requested = max(int(requested), 1)
        total = 0
        max_len = _read_int_env(self.len_env)
        max_out = _read_int_env(self.out_env)
        if max_len is not None:
            total += max(max_len, 0)
        if max_out is not None:
            total += max(max_out, 0)
        floor = total if total > 0 else self.default_total
        return max(requested, floor)


def _read_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


__all__ = ["TotalLengthPolicy"]
