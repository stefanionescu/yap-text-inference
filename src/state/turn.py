"""Turn execution planning dataclasses."""

from __future__ import annotations

from typing import TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from .session import HistoryTurn, SessionState


@dataclass(slots=True)
class TurnPlan:
    """Validated plan for executing one start/message turn."""

    state: SessionState
    request_id: str
    static_prefix: str
    runtime_text: str
    history_turns: list[HistoryTurn]
    chat_user_utt: str | None = None
    tool_user_utt: str | None = None
    history_turn_id: str | None = None
    sampling_overrides: dict[str, float | int] | None = None
    apply_screen_checked_prefix: bool = False


__all__ = ["TurnPlan"]
