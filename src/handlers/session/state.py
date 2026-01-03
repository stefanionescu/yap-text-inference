"""Session state re-exports for backwards compatibility.

The canonical state definitions now live in src/state/session.py.
This module re-exports them for existing imports.

Configuration:
    SESSION_IDLE_TTL_SECONDS: Imported from src/config/timeouts.py
"""

from __future__ import annotations

from src.config.timeouts import SESSION_IDLE_TTL_SECONDS
from src.state import HistoryTurn, SessionState

__all__ = [
    "HistoryTurn",
    "SessionState",
    "SESSION_IDLE_TTL_SECONDS",
]
