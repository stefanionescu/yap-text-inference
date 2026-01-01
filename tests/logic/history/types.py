"""Data types for the history benchmark test suite.

This module defines configuration dataclasses for history benchmark runs.
Similar to the standard benchmark types but includes warm history support.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoryBenchConfig:
    """Configuration for a history benchmark run.

    Unlike the standard benchmark, each connection starts with pre-built
    warm history (WARM_HISTORY) and cycles through recall messages.
    """

    url: str
    api_key: str | None
    gender: str
    personality: str
    chat_prompt: str
    timeout_s: float
    sampling: dict[str, float | int] | None


__all__ = ["HistoryBenchConfig"]

