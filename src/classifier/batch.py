"""Micro-batching primitives for classifier inference."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from typing import Any, Callable

import torch  # type: ignore[import]


class Future:
    """Lightweight, thread-safe future used by the batch executor."""

    def __init__(self) -> None:
        self._event = threading.Event()
        self._result: Any = None
        self._exc: BaseException | None = None

    def set_result(self, result: Any) -> None:
        self._result = result
        self._event.set()

    def set_exception(self, exc: BaseException) -> None:
        self._exc = exc
        self._event.set()

    def result(self, timeout: float | None = None) -> Any:
        if not self._event.wait(timeout):
            raise TimeoutError("Classifier batch timed out")
        if self._exc is not None:
            raise self._exc
        return self._result


@dataclass(slots=True)
class RequestItem:
    text: str
    future: Future


class BatchExecutor:
    """Batch incoming requests and execute them with a shared infer_fn."""

    def __init__(
        self,
        infer_fn: Callable[[list[str]], torch.Tensor],
        max_batch_size: int,
        max_delay_ms: float,
    ) -> None:
        self._infer_fn = infer_fn
        self._max_batch = max(1, int(max_batch_size))
        self._max_delay = max(0.0, float(max_delay_ms)) / 1000.0
        self._queue: "Queue[RequestItem]" = Queue()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def classify(self, text: str, timeout_s: float) -> list[float]:
        fut = Future()
        self._queue.put(RequestItem(text=text, future=fut))
        return fut.result(timeout=timeout_s)

    def _worker_loop(self) -> None:
        while True:
            item = self._queue.get()
            batch = [item]
            deadline = time.perf_counter() + self._max_delay

            while len(batch) < self._max_batch:
                remaining = max(0.0, deadline - time.perf_counter())
                if remaining <= 0:
                    break
                try:
                    batch.append(self._queue.get(timeout=remaining))
                except Empty:
                    break

            texts = [req.text for req in batch]
            try:
                logits = self._infer_fn(texts)
                probs = torch.softmax(logits, dim=-1).detach().cpu().tolist()
                for req, prob in zip(batch, probs, strict=False):
                    req.future.set_result(prob)
            except Exception as exc:  # noqa: BLE001
                for req in batch:
                    req.future.set_exception(exc)


__all__ = ["BatchExecutor"]
