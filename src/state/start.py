"""Start message execution dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class StartPlan:
    """Validated plan for executing a start message."""

    session_id: str
    request_id: str
    static_prefix: str
    runtime_text: str
    history_text: str
    user_utt: str
    history_turn_id: str | None = None
    sampling_overrides: dict[str, float | int] | None = None


__all__ = ["StartPlan"]
