"""Data types for the tool regression test suite.

This module defines the dataclasses used throughout the tool test infrastructure:
test case definitions, runner configuration, turn results, timing metrics,
failure records, and overall case results.
"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class CaseStep:
    """A single step in a tool test case."""

    text: str
    expect_tool: bool | None = None


@dataclass(frozen=True)
class ToolTestCase:
    """A complete tool test case with one or more steps."""

    uid: int
    name: str
    label: str
    steps: Sequence[CaseStep]


@dataclass(frozen=True)
class RunnerConfig:
    """Configuration for the tool test runner.
    
    Note: chat_prompt is required - the server requires a system prompt
    when DEPLOY_CHAT is enabled.
    """

    ws_url: str
    gender: str
    personality: str
    chat_prompt: str  # Required - use select_chat_prompt(gender) to get one
    timeout_s: float
    ping_interval: int
    ping_timeout: int


@dataclass(frozen=True)
class TurnResult:
    """Result of a single turn in a tool test case."""

    ok: bool
    tool_called: bool | None
    tool_status: str | None
    tool_raw: Any
    chat_seen: bool
    reason: str | None = None
    detail: str | None = None
    ttfb_s: float | None = None
    total_s: float | None = None


@dataclass(frozen=True)
class StepTiming:
    """Timing metrics for a single step."""

    step_index: int
    ttfb_ms: float | None
    total_ms: float | None


@dataclass(frozen=True)
class FailureRecord:
    """Details about a single failure within a test case."""

    reason: str
    detail: str
    failing_step: int
    expected: bool | None
    actual: bool | None


@dataclass(frozen=True)
class CaseResult:
    """Overall result for a complete test case."""

    case: ToolTestCase
    success: bool
    reason: str | None = None
    detail: str | None = None
    failing_step: int | None = None
    expected: bool | None = None
    actual: bool | None = None
    responses: list[Any] | None = None
    step_timings: list[StepTiming] | None = None
    failures: list[FailureRecord] | None = None


__all__ = [
    "CaseStep",
    "ToolTestCase",
    "RunnerConfig",
    "TurnResult",
    "StepTiming",
    "FailureRecord",
    "CaseResult",
]
