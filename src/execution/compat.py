"""Async compatibility helpers for Python 3.10+.

Provides replacements for asyncio features added in Python 3.11.
"""

from __future__ import annotations

import asyncio
import contextlib
from typing import TypeVar
from collections.abc import AsyncGenerator

T = TypeVar("T")


@contextlib.asynccontextmanager
async def timeout(delay: float) -> AsyncGenerator[None, None]:
    """Async context manager that cancels the block after delay seconds.

    Compatible replacement for asyncio.timeout() which requires Python 3.11+.

    Args:
        delay: Timeout in seconds.

    Raises:
        asyncio.TimeoutError: If the block does not complete within delay.

    Usage:
        async with timeout(5.0):
            await some_operation()
    """
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    if task is None:
        raise RuntimeError("timeout() must be called from within a task")

    deadline = loop.time() + delay
    timed_out = False

    def on_timeout() -> None:
        nonlocal timed_out
        timed_out = True
        task.cancel()

    handle = loop.call_at(deadline, on_timeout)
    try:
        yield
    except asyncio.CancelledError:
        if timed_out:
            raise asyncio.TimeoutError() from None
        raise
    finally:
        handle.cancel()


__all__ = ["timeout"]
