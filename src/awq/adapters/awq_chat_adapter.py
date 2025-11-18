#!/usr/bin/env python3
"""Chat model helpers for AWQ quantization."""

from __future__ import annotations

import os

_CHAT_DEFAULT_TOTAL_LEN = 5360


def _read_int_env(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def compute_chat_calibration_seqlen(requested: int) -> int:
    chat_max_len = _read_int_env("CHAT_MAX_LEN")
    chat_max_out = _read_int_env("CHAT_MAX_OUT")

    total = 0
    if chat_max_len is not None:
        total += chat_max_len
    if chat_max_out is not None:
        total += chat_max_out

    if total > 0:
        return max(requested, total)

    return max(requested, _CHAT_DEFAULT_TOTAL_LEN)


__all__ = ["compute_chat_calibration_seqlen"]
