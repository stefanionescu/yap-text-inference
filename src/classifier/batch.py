"""Micro-batching primitives for classifier inference.

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

import threading
import time
from dataclasses import dataclass
from queue import Empty, Queue
from collections.abc import Callable

import torch  # type: ignore[import]


class BatchFuture:
    """Lightweight, thread-safe future for batch executor results.
    
    Simpler than asyncio.Future or concurrent.futures.Future,
    optimized for the specific use case of cross-thread result delivery.
    
    Thread Safety:
        Uses threading.Event for synchronization.
        Safe to call set_result/set_exception from one thread
        and result() from another.
    """

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
        """Wait for and return the result, or raise the stored exception.
        
        Args:
            timeout: Max seconds to wait (None = forever).
            
        Returns:
            List of class probabilities.
            
        Raises:
            TimeoutError: If timeout expires before result is set.
            Exception: The stored exception if set_exception was called.
        """
        if not self._event.wait(timeout):
            raise TimeoutError("Classifier batch timed out")
        if self._exc is not None:
            raise self._exc
        assert self._result is not None
        return self._result


@dataclass(slots=True)
class RequestItem:
    """A single classification request pending execution.
    
    Attributes:
        text: The text to classify.
        future: Future to receive the classification result.
    """
    text: str
    future: BatchFuture


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
            probs = torch.softmax(logits, dim=-1).detach().cpu().tolist()
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
