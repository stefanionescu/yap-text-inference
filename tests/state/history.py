"""Data types for the history benchmark test suite."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryBenchConfig:
    """Configuration for a history benchmark run."""

    url: str
    api_key: str | None
    gender: str
    personality: str
    chat_prompt: str
    timeout_s: float
    sampling: dict[str, float | int] | None


__all__ = ["HistoryBenchConfig"]
