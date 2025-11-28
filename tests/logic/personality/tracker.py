"""Stream metrics tracking for personality tests."""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass, field
from typing import Any

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.helpers.regex import contains_complete_sentence, has_at_least_n_words


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


@dataclass
class StreamTracker:
    """Tracks timing metrics for a single request/response cycle."""

    sent_ts: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    first_token_ts: float | None = None
    first_sentence_ts: float | None = None
    first_3_words_ts: float | None = None
    toolcall_ttfb_ts: float | None = None
    chunks: int = 0

    def reset(self) -> None:
        """Reset tracker for a new request."""
        self.sent_ts = time.perf_counter()
        self.final_text = ""
        self.first_token_ts = None
        self.first_sentence_ts = None
        self.first_3_words_ts = None
        self.toolcall_ttfb_ts = None
        self.chunks = 0

    def _ms_since_sent(self, timestamp: float | None) -> float | None:
        if timestamp is None:
            return None
        return (timestamp - self.sent_ts) * 1000.0

    def record_toolcall(self) -> float | None:
        """Record toolcall TTFB (first toolcall message)."""
        if self.toolcall_ttfb_ts is None:
            self.toolcall_ttfb_ts = time.perf_counter()
        return self._ms_since_sent(self.toolcall_ttfb_ts)

    def record_token(self, chunk: str) -> dict[str, float | None]:
        """Record chat token and update metrics."""
        metrics: dict[str, float | None] = {}
        if not chunk:
            return metrics

        if self.first_token_ts is None:
            self.first_token_ts = time.perf_counter()
            metrics["ttfb_chat_ms"] = self._ms_since_sent(self.first_token_ts)

        self.final_text += chunk
        self.chunks += 1

        if self.first_3_words_ts is None and has_at_least_n_words(self.final_text, 3):
            self.first_3_words_ts = time.perf_counter()
            metrics["first_3_words_ms"] = self._ms_since_sent(self.first_3_words_ts)

        if self.first_sentence_ts is None and contains_complete_sentence(self.final_text):
            self.first_sentence_ts = time.perf_counter()
            metrics["first_sentence_ms"] = self._ms_since_sent(self.first_sentence_ts)

        return metrics

    def finalize_metrics(self) -> dict[str, Any]:
        """Produce final metrics dict after response is complete."""
        done_ts = time.perf_counter()
        total_ms = (done_ts - self.sent_ts) * 1000.0
        stream_ms = None
        if self.first_token_ts is not None:
            stream_ms = (done_ts - self.first_token_ts) * 1000.0

        return {
            "ttfb_toolcall_ms": _round(self._ms_since_sent(self.toolcall_ttfb_ts)),
            "ttfb_chat_ms": _round(self._ms_since_sent(self.first_token_ts)),
            "first_3_words_ms": _round(self._ms_since_sent(self.first_3_words_ts)),
            "first_sentence_ms": _round(self._ms_since_sent(self.first_sentence_ts)),
            "total_ms": _round(total_ms),
            "stream_ms": _round(stream_ms),
            "chunks": self.chunks,
            "chars": len(self.final_text),
        }


