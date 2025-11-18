"""Streaming helpers shared by chat and tool executors."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any
from collections.abc import AsyncGenerator, Awaitable, Callable


CancelCheck = Callable[[], bool | Awaitable[bool]] | None


class StreamCancelledError(Exception):
    """Raised when a cooperative cancel check requests termination."""


async def stream_with_timeout(
    get_engine: Callable[[], Awaitable[Any]],
    prompt: str,
    sampling_params: Any,
    request_id: str,
    priority: int,
    timeout_s: float,
    cancel_check: CancelCheck = None,
) -> AsyncGenerator[Any, None]:
    """Yield engine stream outputs with a hard timeout and optional cancellation."""
    engine = await get_engine()
    stream = engine.generate(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
        priority=priority,
    )
    cancel_checker = _CancelChecker(cancel_check)

    try:
        async with asyncio.timeout(timeout_s):
            async for out in stream:
                if await cancel_checker.triggered():
                    await _abort_request(engine, request_id)
                    raise StreamCancelledError()
                yield out
    except asyncio.TimeoutError:
        await _abort_request(engine, request_id)
        raise


async def _abort_request(engine: Any, request_id: str) -> None:
    with contextlib.suppress(Exception):
        await engine.abort_request(request_id)


class _CancelChecker:
    def __init__(self, cancel_check: CancelCheck):
        self._check = cancel_check

    async def triggered(self) -> bool:
        if self._check is None:
            return False
        result = self._check()
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)
