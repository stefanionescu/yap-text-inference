"""Data types for the history benchmark test suite."""

from __future__ import annotations

from dataclasses import dataclass
from .metrics import StartPayloadMode


@dataclass(frozen=True)
class HistoryBenchConfig:
    """Configuration for a history benchmark run."""

    url: str
    api_key: str | None
    gender: str | None
    personality: str | None
    chat_prompt: str | None
    timeout_s: float
    sampling: dict[str, float | int] | None
    start_payload_mode: StartPayloadMode = "all"


__all__ = ["HistoryBenchConfig"]
