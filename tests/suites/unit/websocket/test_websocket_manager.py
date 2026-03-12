"""Unit tests for websocket manager rate-limiter wiring."""

from __future__ import annotations

from src.handlers.websocket.manager import _create_rate_limiters
from src.config.websocket import WS_RATE_LIMIT_WINDOW, WS_MAX_CANCELS_PER_WINDOW, WS_MAX_MESSAGES_PER_WINDOW


def test_create_rate_limiters_use_shared_window_and_configured_limits() -> None:
    message_limiter, cancel_limiter = _create_rate_limiters()

    assert message_limiter.limit == WS_MAX_MESSAGES_PER_WINDOW
    assert cancel_limiter.limit == WS_MAX_CANCELS_PER_WINDOW
    assert message_limiter.window_seconds == WS_RATE_LIMIT_WINDOW
    assert cancel_limiter.window_seconds == WS_RATE_LIMIT_WINDOW
