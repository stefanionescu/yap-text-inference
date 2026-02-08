"""Data types for tool regression tests."""

from __future__ import annotations

import time
from typing import Any
from collections.abc import Sequence
from dataclasses import field, dataclass


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
    """Configuration for the tool test runner."""

    ws_url: str
    gender: str
    personality: str
    chat_prompt: str
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


@dataclass
class DrainState:
    """Mutable state tracked during response draining."""

    tool_status: str | None = None
    tool_raw: Any = None
    chat_seen: bool = False
    done: bool = False
    cancelled: bool = False
    error: dict[str, Any] | None = None
    first_tool_frame_s: float | None = None
    last_tool_frame_s: float | None = None
    tool_decision_received: bool = False


@dataclass
class DrainConfig:
    """Configuration for response draining."""

    timeout_s: float
    chat_idle_timeout_s: float | None
    start_ts: float = field(default_factory=time.perf_counter)

    @property
    def tool_deadline(self) -> float:
        return self.start_ts + self.timeout_s


__all__ = [
    "CaseResult",
    "CaseStep",
    "DrainConfig",
    "DrainState",
    "FailureRecord",
    "RunnerConfig",
    "StepTiming",
    "ToolTestCase",
    "TurnResult",
]
