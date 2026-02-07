"""Data types for the benchmark test suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for a benchmark run."""

    url: str
    api_key: str | None
    gender: str
    style: str
    chat_prompt: str
    message: str
    timeout_s: float
    sampling: dict[str, float | int] | None
    double_ttfb: bool


@dataclass
class TransactionMetrics:
    """Timing metrics for a single benchmark transaction."""

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
