"""Helpers for phase-scoped telemetry annotations."""

from __future__ import annotations

from .instruments import get_metrics


def record_phase_latency(phase: str, seconds: float) -> None:
    """Record latency for an execution phase."""
    get_metrics().phase_latency.record(max(0.0, seconds), {"phase": phase})


def record_phase_error(phase: str, error_type: str) -> None:
    """Increment phase-scoped error counter."""
    get_metrics().phase_errors_total.add(1, {"phase": phase, "error.type": error_type})


__all__ = ["record_phase_latency", "record_phase_error"]
