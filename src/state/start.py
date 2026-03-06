"""Start message execution dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .session import SessionState, HistoryTurn


@dataclass(slots=True)
class StartPlan:
    """Validated plan for executing a start message."""

    state: SessionState
    request_id: str
    static_prefix: str
    runtime_text: str
    history_turns: list[HistoryTurn]
    user_utt: str
    history_turn_id: str | None = None
    sampling_overrides: dict[str, float | int] | None = None


__all__ = ["StartPlan"]
