"""Thread-safe future primitive for tool micro-batching."""

from __future__ import annotations

import threading


class BatchFuture:
    """Lightweight, thread-safe future for batch executor results."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._result: list[float] | None = None
        self._exc: Exception | None = None

    def set_result(self, result: list[float]) -> None:
        """Set the result value and wake waiters."""
        self._result = result
        self._event.set()

    def set_exception(self, exc: Exception) -> None:
        """Set an exception to be raised and wake waiters."""
        self._exc = exc
        self._event.set()

    def result(self, timeout: float | None = None) -> list[float]:
        """Wait for and return the result, or raise the stored exception."""
        if not self._event.wait(timeout):
            raise TimeoutError("Tool batch timed out")
        if self._exc is not None:
            raise self._exc
        if self._result is None:
            raise RuntimeError("Tool batch completed without result")
        return self._result


__all__ = ["BatchFuture"]
