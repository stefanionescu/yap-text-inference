#!/usr/bin/env python3
"""Chat model helpers for AWQ quantization."""

from __future__ import annotations

from src.config.awq import CHAT_TOTAL_POLICY, resolve_total_len


def compute_chat_calibration_seqlen(requested: int) -> int:
    """Return the calibration sequence length floor for chat models."""
    return resolve_total_len(requested, CHAT_TOTAL_POLICY)


__all__ = ["compute_chat_calibration_seqlen"]
