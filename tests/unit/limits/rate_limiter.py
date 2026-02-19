"""Unit tests for sliding window rate limiter."""

from __future__ import annotations

import pytest

from src.errors import RateLimitError
from src.handlers.limits import SlidingWindowRateLimiter


def test_consume_under_limit_succeeds() -> None:
    t = 0.0

    def now_fn() -> float:
        return t

    limiter = SlidingWindowRateLimiter(limit=3, window_seconds=10.0, now_fn=now_fn)
    limiter.consume()
    limiter.consume()
    # Two consumes under limit of 3 — no error


def test_consume_at_limit_raises() -> None:
    t = 0.0

    def now_fn() -> float:
        return t

    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=10.0, now_fn=now_fn)
    limiter.consume()
    limiter.consume()
    with pytest.raises(RateLimitError) as exc_info:
        limiter.consume()
    assert exc_info.value.limit == 2
    assert exc_info.value.window_seconds == 10.0
    assert exc_info.value.retry_in >= 0.0


def test_rate_limit_error_has_correct_metadata() -> None:
    clock = [0.0]

    def now_fn() -> float:
        return clock[0]

    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=5.0, now_fn=now_fn)
    limiter.consume()
    clock[0] = 1.0
    with pytest.raises(RateLimitError) as exc_info:
        limiter.consume()
    err = exc_info.value
    assert err.limit == 1
    assert err.window_seconds == 5.0
    assert err.retry_in == pytest.approx(4.0, abs=0.1)


def test_consume_after_window_expires() -> None:
    clock = [0.0]

    def now_fn() -> float:
        return clock[0]

    limiter = SlidingWindowRateLimiter(limit=1, window_seconds=5.0, now_fn=now_fn)
    limiter.consume()
    # Advance past window
    clock[0] = 6.0
    limiter.consume()  # Should succeed


def test_disabled_limiter_limit_zero() -> None:
    limiter = SlidingWindowRateLimiter(limit=0, window_seconds=10.0)
    for _ in range(100):
        limiter.consume()  # Never raises


def test_disabled_limiter_window_zero() -> None:
    limiter = SlidingWindowRateLimiter(limit=10, window_seconds=0.0)
    for _ in range(100):
        limiter.consume()  # Never raises
