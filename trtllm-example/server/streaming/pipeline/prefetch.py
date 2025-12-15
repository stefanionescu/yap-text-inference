"""Helpers for prefetching PCM chunks off the TensorRT queue."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from tensorrt_llm import SamplingParams

from server.streaming.pipeline.tts_streaming import aiter_pcm_from_custom_tokens

__all__ = ["ChunkPrefetcher"]


@dataclass(slots=True)
class ChunkPrefetcher:
    """Generate PCM for a text chunk into an asyncio queue."""

    engine: Any
    voice: str
    sampling_template: dict
    trim_silence: bool
    prepad_ms: float | None
    cancel_event: asyncio.Event | None

    async def run(self, text: str, queue: asyncio.Queue[bytes | None]) -> None:
        sampling_params = SamplingParams(**self.sampling_template)
        try:
            async for pcm in aiter_pcm_from_custom_tokens(
                self.engine, text, self.voice, sampling_params, trim_silence=self.trim_silence, prepad_ms=self.prepad_ms
            ):
                if self.cancel_event is not None and self.cancel_event.is_set():
                    break
                await queue.put(pcm)
        finally:
            await queue.put(None)
