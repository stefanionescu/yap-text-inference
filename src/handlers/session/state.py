"""Session state re-exports for backwards compatibility.

The canonical state definitions live in the state module.
This module re-exports them for existing imports.

Configuration:
    SESSION_IDLE_TTL_SECONDS: Imported from the timeouts config
"""

from __future__ import annotations

from src.state import HistoryTurn, SessionState
from src.config.timeouts import SESSION_IDLE_TTL_SECONDS

__all__ = [
    "HistoryTurn",
    "SessionState",
    "SESSION_IDLE_TTL_SECONDS",
]
