"""Shared dataclasses for the tool regression suite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

__all__ = [
    "CaseStep",
    "ToolTestCase",
    "RunnerConfig",
    "TurnResult",
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
    chat_prompt: str
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


@dataclass(frozen=True)
class CaseResult:
    case: ToolTestCase
    success: bool
    reason: str | None = None
    detail: str | None = None
    failing_step: int | None = None
    expected: bool | None = None
    actual: bool | None = None

