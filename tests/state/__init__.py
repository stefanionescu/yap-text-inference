"""Centralized dataclasses for test state and helpers."""

from .history import HistoryBenchConfig
from .conversation import ConversationSession
from .benchmark import BenchmarkConfig, TransactionMetrics
from .live import LiveSession, StreamResult, PersonaDefinition
from .metrics import StreamState, TTFBSamples, SessionContext, BenchmarkResultData
from .cancel import DrainPhaseResult, CancelPhaseResult, CancelClientResult, NormalClientResult, RecoveryPhaseResult
from .tool import (
    CaseStep,
    CaseResult,
    DrainState,
    StepTiming,
    TurnResult,
    DrainConfig,
    RunnerConfig,
    ToolTestCase,
    FailureRecord,
)

__all__ = [
    "BenchmarkConfig",
    "BenchmarkResultData",
    "CancelClientResult",
    "CancelPhaseResult",
    "CaseResult",
    "CaseStep",
    "ConversationSession",
    "DrainConfig",
    "DrainPhaseResult",
    "DrainState",
    "FailureRecord",
    "HistoryBenchConfig",
    "LiveSession",
    "NormalClientResult",
    "PersonaDefinition",
    "RecoveryPhaseResult",
    "RunnerConfig",
    "SessionContext",
    "StepTiming",
    "StreamResult",
    "StreamState",
    "TTFBSamples",
    "ToolTestCase",
    "TransactionMetrics",
    "TurnResult",
]
