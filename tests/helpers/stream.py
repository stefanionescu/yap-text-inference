"""Streaming token metrics tracker for test utilities.

This module provides the StreamTracker dataclass that accumulates timing
metrics as tokens stream in from the server. It tracks time-to-first-token,
time-to-first-sentence, time-to-first-3-words, and total response metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from .math import round_ms
from .regex import contains_complete_sentence, has_at_least_n_words


@dataclass
class StreamTracker:
    """Track streaming token metrics shared by the CLI utilities."""

    sent_ts: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    ack_seen: bool = False
    first_token_ts: float | None = None
    first_sentence_ts: float | None = None
    first_3_words_ts: float | None = None
    toolcall_ttfb_ms: float | None = None
    chunks: int = 0

    def _ms_since_sent(self, timestamp: float | None) -> float | None:
        """Calculate milliseconds elapsed since the request was sent."""
        if timestamp is None:
            return None
        return (timestamp - self.sent_ts) * 1000.0

    def record_toolcall(self) -> float | None:
        """Record the time-to-first-byte for tool call response."""
        now = time.perf_counter()
        self.toolcall_ttfb_ms = self._ms_since_sent(now)
        return self.toolcall_ttfb_ms

    def record_token(self, chunk: str) -> dict[str, float | None]:
        """Record a streaming token and return any newly triggered metrics.
        
        Returns a dict with keys that may include:
            - chat_ttfb_ms / ttfb_chat_ms: Time to first chat token
            - time_to_first_3_words_ms / first_3_words_ms: Time to first 3 words
            - time_to_first_complete_sentence_ms / first_sentence_ms: Time to first sentence
        
        Both key variants are provided for backwards compatibility.
        """
        metrics: dict[str, float | None] = {}
        if not chunk:
            return metrics

        if self.first_token_ts is None:
            self.first_token_ts = time.perf_counter()
            ttfb = self._ms_since_sent(self.first_token_ts)
            metrics["chat_ttfb_ms"] = ttfb
            metrics["ttfb_chat_ms"] = ttfb  # Alias for backwards compat

        self.final_text += chunk
        if self.first_3_words_ts is None and has_at_least_n_words(self.final_text, 3):
            self.first_3_words_ts = time.perf_counter()
            first_3 = self._ms_since_sent(self.first_3_words_ts)
            metrics["time_to_first_3_words_ms"] = first_3
            metrics["first_3_words_ms"] = first_3  # Alias for backwards compat

        if self.first_sentence_ts is None and contains_complete_sentence(self.final_text):
            self.first_sentence_ts = time.perf_counter()
            first_sentence = self._ms_since_sent(self.first_sentence_ts)
            metrics["time_to_first_complete_sentence_ms"] = first_sentence
            metrics["first_sentence_ms"] = first_sentence  # Alias for backwards compat

        self.chunks += 1
        return metrics

    def finalize_metrics(self, cancelled: bool = False) -> dict[str, Any]:
        """Build the final metrics dict after streaming completes."""
        done_ts = time.perf_counter()
        ttfb_ms = self._ms_since_sent(self.first_token_ts)
        stream_ms = None
        if self.first_token_ts is not None:
            stream_ms = (done_ts - self.first_token_ts) * 1000.0
        total_ms = (done_ts - self.sent_ts) * 1000.0
        return {
            "ok": not cancelled,
            "ttfb_ms": round_ms(ttfb_ms),
            "ttfb_chat_ms": round_ms(ttfb_ms),
            "ttfb_toolcall_ms": round_ms(self.toolcall_ttfb_ms),
            "total_ms": round_ms(total_ms),
            "stream_ms": round_ms(stream_ms),
            "time_to_first_complete_sentence_ms": round_ms(self._ms_since_sent(self.first_sentence_ts)),
            "time_to_first_3_words_ms": round_ms(self._ms_since_sent(self.first_3_words_ts)),
            "chunks": self.chunks,
            "chars": len(self.final_text),
        }


__all__ = ["StreamTracker", "round_ms"]
