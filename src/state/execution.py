"""Execution-related dataclasses."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from collections.abc import Callable, Awaitable

if TYPE_CHECKING:
    from src.engines.base import BaseEngine

CancelCheck = Callable[[], bool | Awaitable[bool]] | None


@dataclass(slots=True)
class ChatStreamConfig:
    """Configuration for chat streaming."""

    session_id: str
    request_id: str
    prompt: str
    sampling_params: Any
    engine_getter: Callable[[], Awaitable[BaseEngine]]
    timeout_s: float
    flush_ms: float = 0.0
    cancel_check: CancelCheck = None


__all__ = ["ChatStreamConfig", "CancelCheck"]
