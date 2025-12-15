"""Queue draining helpers for streaming PCM to WebSocket clients."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

SentenceStartSender = Callable[[Any, str, str | None, asyncio.Event | None], Awaitable[bool]]
AudioEndSender = Callable[[Any, str | None], Awaitable[None]]

__all__ = ["QueuedChunkDrainer"]


@dataclass(slots=True)
class QueuedChunkDrainer:
    """Drain PCM bytes from a queue to a WebSocket."""

    queue: asyncio.Queue[bytes | None]
    ws: Any
    cancel_event: asyncio.Event | None
    sentence_text: str
    request_id: str | None
    send_sentence_start: SentenceStartSender
    send_audio_end: AudioEndSender

    async def run(self) -> tuple[bool, bool]:
        """
        Drain all PCM data from queue to WebSocket.

        Returns (queue_completed_normally, sentence_header_sent).
        """
        sentence_header_sent = False
        while True:
            cancelled, pcm = await self._queue_get_with_cancel()
            if cancelled:
                await self.send_audio_end(self.ws, self.request_id)
                return False, sentence_header_sent
            if pcm is None:
                break
            if self.cancel_event is not None and self.cancel_event.is_set():
                await self.send_audio_end(self.ws, self.request_id)
                return False, sentence_header_sent
            if not sentence_header_sent:
                sentence_header_sent = await self.send_sentence_start(
                    self.ws, self.sentence_text, self.request_id, self.cancel_event
                )
            await self.ws.send_bytes(pcm)
        return True, sentence_header_sent

    async def _queue_get_with_cancel(self) -> tuple[bool, bytes | None]:
        if self.cancel_event is None:
            return False, await self.queue.get()

        queue_task: asyncio.Task[bytes | None] = asyncio.create_task(self.queue.get())
        cancel_task: asyncio.Task[bool] = asyncio.create_task(self.cancel_event.wait())

        done, _ = await asyncio.wait({queue_task, cancel_task}, return_when=asyncio.FIRST_COMPLETED)

        if cancel_task in done:
            queue_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await queue_task
            return True, None

        cancel_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await cancel_task

        return False, queue_task.result()
