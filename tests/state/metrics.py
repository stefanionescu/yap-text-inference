"""Shared data types for test utilities."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionContext:
    """Immutable context for building session payloads."""

    session_id: str
    gender: str
    personality: str
    chat_prompt: str
    sampling: dict[str, float | int] | None = None


@dataclass
class StreamState:
    """Mutable state for stream metric tracking."""

    sent_ts: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    ack_seen: bool = False
    first_token_ts: float | None = None
    first_sentence_ts: float | None = None
    first_3_words_ts: float | None = None
    toolcall_ttfb_ms: float | None = None
    toolcall_status: str | None = None
    toolcall_raw: dict | None = None
    chunks: int = 0


@dataclass
class TTFBSamples:
    """Accumulated TTFB and latency samples."""

    tool_samples: list[float] = field(default_factory=list)
    chat_samples: list[float] = field(default_factory=list)
    first_3_words_samples: list[float] = field(default_factory=list)
    first_sentence_samples: list[float] = field(default_factory=list)


@dataclass
class BenchmarkResultData:
    """Result data for a single benchmark transaction."""

    ok: bool
    phase: int = 1
    error: str | None = None
    error_code: str | None = None
    recoverable: bool = False
    ttfb_toolcall_ms: float | None = None
    ttfb_chat_ms: float | None = None
    first_sentence_ms: float | None = None
    first_3_words_ms: float | None = None


__all__ = [
    "BenchmarkResultData",
    "SessionContext",
    "StreamState",
    "TTFBSamples",
]
