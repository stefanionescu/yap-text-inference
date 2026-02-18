"""Micro-batching primitives for tool inference.

This module provides infrastructure for accumulating individual classification
requests into batches for efficient GPU inference. Key components:

BatchFuture:
    A lightweight, thread-safe promise/future implementation for returning
    results from the worker thread to requesting threads.

RequestItem:
    Simple dataclass pairing a text to classify with its result BatchFuture.

BatchExecutor:
    The main batching coordinator that:
    1. Accepts individual classify() calls from multiple threads
    2. Accumulates requests in a queue
    3. Runs a background worker that batches requests
    4. Limits batch size (max_batch_size) and wait time (max_delay_ms)
    5. Dispatches batches to the inference function
    6. Distributes results back to waiting callers

This micro-batching approach is critical for efficient GPU utilization when
handling many small classification requests concurrently.
"""

from __future__ import annotations

import time
import threading
from queue import Empty, Queue
from collections.abc import Callable

import torch  # type: ignore[import]

from src.state import RequestItem

from .future import BatchFuture


class BatchExecutor:
    """Batch incoming requests and execute them with a shared infer_fn.

    This executor implements adaptive micro-batching:
    - Waits up to max_delay_ms for more requests to arrive
    - Batches up to max_batch_size requests together
    - Runs inference on the batch
    - Distributes results to individual callers

    The background worker thread runs continuously, processing
    batches as they become ready.
    """

    def __init__(
        self,
        infer_fn: Callable[[list[str]], torch.Tensor],
        max_batch_size: int,
        max_delay_ms: float,
    ) -> None:
        """Initialize the batch executor.

        Args:
            infer_fn: Function that takes list of texts and returns logits tensor.
            max_batch_size: Maximum requests to batch together.
            max_delay_ms: Maximum milliseconds to wait for more requests.
        """
        self._infer_fn = infer_fn
        self._max_batch = max(1, int(max_batch_size))
        self._max_delay = max(0.0, float(max_delay_ms)) / 1000.0
        self._queue: Queue[RequestItem] = Queue()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def classify(self, text: str, timeout_s: float) -> list[float]:
        """Submit a text for classification and wait for result.

        Args:
            text: Text to classify.
            timeout_s: Maximum seconds to wait for result.

        Returns:
            List of class probabilities (softmax of logits).

        Raises:
            TimeoutError: If result not ready within timeout.
        """
        fut = BatchFuture()
        self._queue.put(RequestItem(text=text, future=fut))
        return fut.result(timeout=timeout_s)

    def _collect_batch(self) -> list[RequestItem]:
        """Block until at least one request, then collect up to max_batch."""
        first = self._queue.get()
        batch = [first]
        deadline = time.perf_counter() + self._max_delay

        while len(batch) < self._max_batch:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break
            try:
                batch.append(self._queue.get(timeout=remaining))
            except Empty:
                break

        return batch

    def _dispatch_batch(self, batch: list[RequestItem]) -> None:
        """Run inference on batch and deliver results to futures."""
        texts = [req.text for req in batch]
        try:
            logits = self._infer_fn(texts)
            probs = torch.softmax(logits.detach().cpu(), dim=-1).tolist()
            if len(probs) != len(batch):
                raise RuntimeError(f"Batch size mismatch: {len(batch)} requests, {len(probs)} results")
            for req, prob in zip(batch, probs, strict=True):
                req.future.set_result(prob)
        except Exception as exc:  # noqa: BLE001
            for req in batch:
                req.future.set_exception(exc)

    def _worker_loop(self) -> None:
        """Background worker: collect batches and dispatch them."""
        while True:
            batch = self._collect_batch()
            self._dispatch_batch(batch)


__all__ = ["BatchExecutor"]
