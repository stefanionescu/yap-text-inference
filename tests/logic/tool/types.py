"""Shared dataclasses for the tool regression suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

__all__ = [
    "CaseStep",
    "ToolTestCase",
    "RunnerConfig",
    "TurnResult",
    "StepTiming",
    "FailureRecord",
    "CaseResult",
]


@dataclass(frozen=True)
class CaseStep:
    text: str
    expect_tool: bool | None = None


@dataclass(frozen=True)
class ToolTestCase:
    uid: int
    name: str
    label: str
    steps: Sequence[CaseStep]


@dataclass(frozen=True)
class RunnerConfig:
    ws_url: str
    gender: str
    personality: str
    chat_prompt: str | None
    timeout_s: float
    ping_interval: int
    ping_timeout: int


@dataclass(frozen=True)
class TurnResult:
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
    step_index: int
    ttfb_ms: float | None
    total_ms: float | None


@dataclass(frozen=True)
class FailureRecord:
    reason: str
    detail: str
    failing_step: int
    expected: bool | None
    actual: bool | None


@dataclass(frozen=True)
class CaseResult:
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

