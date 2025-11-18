"""Streaming helpers shared by chat and tool executors."""

from __future__ import annotations

import asyncio
from typing import Any
from collections.abc import AsyncGenerator, Awaitable, Callable


CancelCheck = Callable[[], bool | Awaitable[bool]] | None


async def stream_with_timeout(
    get_engine: Callable[[], Awaitable[Any]],
    prompt: str,
    sampling_params: Any,
    request_id: str,
    priority: int,
    timeout_s: float,
    cancel_check: CancelCheck = None,
) -> AsyncGenerator[Any, None]:
    """Yield engine stream outputs with a hard timeout and optional cancel check.

    The caller is responsible for interpreting outputs and building text deltas.
    Aborts the request on timeout or when the cancel_check returns True.
    """
    engine = await get_engine()
    stream = engine.generate(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
        priority=priority,
    )

    deadline = asyncio.get_event_loop().time() + timeout_s
    aiter = stream.__aiter__()

    while True:
        remaining = deadline - asyncio.get_event_loop().time()
        if remaining <= 0:
            try:
                await engine.abort_request(request_id)
            except Exception:
                pass
            raise asyncio.TimeoutError()

        try:
            out = await asyncio.wait_for(aiter.__anext__(), timeout=remaining)
        except StopAsyncIteration:
            break

        # Optional cooperative cancel
        if cancel_check is not None:
            check = cancel_check()
            if asyncio.iscoroutine(check):
                check = await check  # type: ignore[assignment]
            if check:
                try:
                    await engine.abort_request(request_id)
                except Exception:
                    pass
                return

        yield out


