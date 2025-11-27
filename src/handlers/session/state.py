"""Session-scoped dataclasses and shared state helpers."""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any

from src.utils import SlidingWindowRateLimiter

SESSION_IDLE_TTL_SECONDS = int(os.getenv("SESSION_IDLE_TTL_SECONDS", "1800"))


@dataclass
class HistoryTurn:
    """One user/assistant exchange in the running conversation."""

    turn_id: str
    user: str
    assistant: str


@dataclass
class SessionState:
    """Container for all mutable session-scoped data."""

    session_id: str
    meta: dict[str, Any]
    history_turns: list[HistoryTurn] = field(default_factory=list)
    task: asyncio.Task | None = None
    active_request_id: str | None = None
    tool_request_id: str | None = None
    created_at: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)
    chat_prompt_last_update_at: float = 0.0
    chat_prompt_rate_limiter: SlidingWindowRateLimiter | None = None

    def touch(self) -> None:
        """Mark the session as active."""

        self.last_access = time.monotonic()


