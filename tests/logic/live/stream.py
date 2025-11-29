from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from tests.helpers.regex import contains_complete_sentence, has_at_least_n_words


@dataclass
class StreamTracker:
    sent_ts: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    ack_seen: bool = False
    first_token_ts: float | None = None
    first_sentence_ts: float | None = None
    first_3_words_ts: float | None = None
    toolcall_ttfb_ms: float | None = None
    chunks: int = 0

    def _ms_since_sent(self, timestamp: float | None) -> float | None:
        if timestamp is None:
            return None
        return (timestamp - self.sent_ts) * 1000.0

    def record_toolcall(self) -> float | None:
        now = time.perf_counter()
        self.toolcall_ttfb_ms = self._ms_since_sent(now)
        return self.toolcall_ttfb_ms

    def record_token(self, chunk: str) -> dict[str, float | None]:
        metrics: dict[str, float | None] = {}
        if not chunk:
            return metrics

        if self.first_token_ts is None:
            self.first_token_ts = time.perf_counter()
            metrics["chat_ttfb_ms"] = self._ms_since_sent(self.first_token_ts)

        self.final_text += chunk
        if self.first_3_words_ts is None and has_at_least_n_words(self.final_text, 3):
            self.first_3_words_ts = time.perf_counter()
            metrics["time_to_first_3_words_ms"] = self._ms_since_sent(self.first_3_words_ts)

        if self.first_sentence_ts is None and contains_complete_sentence(self.final_text):
            self.first_sentence_ts = time.perf_counter()
            metrics["time_to_first_complete_sentence_ms"] = self._ms_since_sent(self.first_sentence_ts)

        self.chunks += 1
        return metrics

    def finalize_metrics(self, cancelled: bool) -> dict[str, Any]:
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


def round_ms(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


__all__ = ["StreamTracker", "round_ms"]


