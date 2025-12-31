"""Data types for the benchmark test suite.

This module defines dataclasses for benchmark configuration and result tracking.
Using a config dataclass eliminates the need to pass 9+ parameters through
multiple function layers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for a benchmark run.
    
    Consolidates all session-level options that were previously passed
    as individual parameters through _one_connection, _worker, etc.
    """

    url: str
    api_key: str | None
    gender: str
    style: str
    chat_prompt: str | None
    message: str
    timeout_s: float
    sampling: dict[str, float | int] | None
    double_ttfb: bool


@dataclass
class TransactionMetrics:
    """Timing metrics for a single benchmark transaction.
    
    Tracks TTFB and completion metrics as tokens stream in.
    """

    ttfb_toolcall_ms: float | None = None
    ttfb_chat_ms: float | None = None
    first_sentence_ms: float | None = None
    first_3_words_ms: float | None = None

    def to_result(self, ok: bool, phase: int) -> dict[str, Any]:
        """Convert metrics to a result dict."""
        return {
            "ok": ok,
            "phase": phase,
            "ttfb_toolcall_ms": self.ttfb_toolcall_ms,
            "ttfb_chat_ms": self.ttfb_chat_ms,
            "first_sentence_ms": self.first_sentence_ms,
            "first_3_words_ms": self.first_3_words_ms,
        }


__all__ = [
    "BenchmarkConfig",
    "TransactionMetrics",
]

