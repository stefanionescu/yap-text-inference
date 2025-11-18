"""Async batching wrapper for SNAC decoding."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import numpy as np

from server.audio.snac_processor import SnacProcessor
from server.config import settings

if TYPE_CHECKING:  # pragma: no cover - typing only
    from torch import Tensor as TorchTensor
else:
    TorchTensor = Any

torch = importlib.import_module("torch")


class BatchedSnac:
    """Background worker that batches SNAC decode requests."""

    def __init__(self):
        self.processor = SnacProcessor()
        self.max_batch = settings.snac_max_batch
        self.batch_timeout_ms = settings.snac_batch_timeout_ms
        self._req_q: asyncio.Queue[tuple[list[TorchTensor], asyncio.Future]] | None = None
        self._worker_started = False

    async def decode_codes(self, codes_triplet: list[TorchTensor]) -> np.ndarray:
        """Decode codes asynchronously via the background batch worker."""
        await self._ensure_worker()
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        if self._req_q is None:
            raise RuntimeError("SNAC batch queue was not initialized before decode.")
        await self._req_q.put((codes_triplet, future))
        return await future

    async def _ensure_worker(self) -> None:
        if self._req_q is None:
            self._req_q = asyncio.Queue()
        if not self._worker_started:
            asyncio.create_task(self._batch_worker())
            self._worker_started = True

    async def _batch_worker(self) -> None:
        if self._req_q is None:
            self._req_q = asyncio.Queue()

        while True:
            first_item = await self._req_q.get()
            batch_items = [first_item]

            with contextlib.suppress(Exception):
                await asyncio.sleep(max(0.0, self.batch_timeout_ms / 1000.0))

            while len(batch_items) < self.max_batch:
                try:
                    batch_items.append(self._req_q.get_nowait())
                except asyncio.QueueEmpty:
                    break

            codes_list: list[list[TorchTensor]] = [item[0] for item in batch_items]
            futures = [item[1] for item in batch_items]

            try:
                outputs = self.processor.process_batch(codes_list)

                for future, output in zip(futures, outputs, strict=False):
                    if not future.done():
                        future.set_result(output[0].detach().cpu().numpy())
            except Exception as exc:  # pragma: no cover - defensive path
                for future in futures:
                    if not future.done():
                        future.set_exception(exc)


@lru_cache(maxsize=1)
def get_snac_batched() -> BatchedSnac:
    """Return a singleton `BatchedSnac` instance."""
    return BatchedSnac()
