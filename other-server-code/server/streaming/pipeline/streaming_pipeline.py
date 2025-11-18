"""Streaming pipeline logic coordinating chunking and queue orchestration."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from tensorrt_llm import SamplingParams

from server.config import settings
from server.streaming.pipeline.drain import QueuedChunkDrainer
from server.streaming.pipeline.prefetch import ChunkPrefetcher
from server.streaming.pipeline.tts_streaming import aiter_pcm_from_custom_tokens
from server.text.prompts import chunk_by_sentences
from server.voices import resolve_voice


class StreamingPipeline:
    """Handles text-to-speech synthesis with pipelining for multi-sentence text."""

    def __init__(self, engine):
        self.engine = engine

    async def stream_text(  # noqa: PLR0913
        self,
        text: str,
        voice: str,
        sampling_kwargs: dict,
        ws: Any,
        *,
        trim_silence: bool = True,
        prepad_ms: float | None = None,
        request_id: str | None = None,
        cancel_event: asyncio.Event | None = None,
    ) -> None:
        """Synthesize text and stream PCM audio to WebSocket."""
        sampling_template = self._prepare_sampling_params(sampling_kwargs)
        resolved_voice = self._resolve_voice(voice)
        chunks = chunk_by_sentences(text)

        if not chunks:
            return

        if len(chunks) == 1:
            await self._stream_single_chunk(
                chunks[0],
                resolved_voice,
                sampling_template,
                ws,
                trim_silence,
                prepad_ms,
                cancel_event,
                request_id=request_id,
            )
            return

        await self._stream_chunks_with_pipeline(
            chunks,
            resolved_voice,
            sampling_template,
            ws,
            trim_silence,
            prepad_ms,
            cancel_event,
            request_id=request_id,
        )

    async def _stream_single_chunk(
        self,
        text: str,
        voice: str,
        sampling_template: dict,
        ws: Any,
        trim_silence: bool,
        prepad_ms: float | None,
        cancel_event: asyncio.Event | None,
        request_id: str | None = None,
    ) -> None:
        """Stream a single text chunk directly to WebSocket."""
        if cancel_event is not None and cancel_event.is_set():
            await self._send_audio_end(ws, request_id=request_id)
            return
        sentence_header_sent = False
        sampling_params = self._new_sampling_params(sampling_template)
        async for pcm in aiter_pcm_from_custom_tokens(
            self.engine.engine, text, voice, sampling_params, trim_silence=trim_silence, prepad_ms=prepad_ms
        ):
            if cancel_event is not None and cancel_event.is_set():
                await self._send_audio_end(ws, request_id=request_id)
                return
            if not sentence_header_sent:
                sentence_header_sent = await self._send_sentence_start(ws, text, request_id, cancel_event)
            await ws.send_bytes(pcm)
        if sentence_header_sent:
            await self._send_sentence_end(ws, request_id, cancel_event)

    async def _stream_chunks_with_pipeline(
        self,
        chunks: list[str],
        voice: str,
        sampling_template: dict,
        ws: Any,
        trim_silence: bool,
        prepad_ms: float | None,
        cancel_event: asyncio.Event | None,
        request_id: str | None = None,
    ) -> None:
        """Stream multiple chunks with pipelining for reduced latency."""
        if cancel_event is not None and cancel_event.is_set():
            await self._send_audio_end(ws, request_id=request_id)
            return

        active_queue: asyncio.Queue[bytes | None] | None
        active_task: asyncio.Task[None] | None
        active_queue, active_task = self._start_prefetch_task(
            chunks[1], voice, sampling_template, trim_silence, prepad_ms, cancel_event
        )

        try:
            await self._stream_single_chunk(
                chunks[0],
                voice,
                sampling_template,
                ws,
                trim_silence,
                prepad_ms,
                cancel_event,
                request_id=request_id,
            )

            for idx in range(1, len(chunks)):
                if cancel_event is not None and cancel_event.is_set():
                    await self._send_audio_end(ws, request_id=request_id)
                    return
                if active_queue is None:
                    break

                drainer = QueuedChunkDrainer(
                    queue=active_queue,
                    ws=ws,
                    cancel_event=cancel_event,
                    sentence_text=chunks[idx],
                    request_id=request_id,
                    send_sentence_start=self._send_sentence_start,
                    send_audio_end=self._send_audio_end,
                )
                drained_ok, sentence_header_sent = await drainer.run()
                await self._await_task(active_task)
                active_task = None

                if not drained_ok:
                    return
                if sentence_header_sent:
                    await self._send_sentence_end(ws, request_id, cancel_event)

                if (idx + 1) >= len(chunks):
                    break

                active_queue, active_task = self._start_prefetch_task(
                    chunks[idx + 1],
                    voice,
                    sampling_template,
                    trim_silence,
                    prepad_ms,
                    cancel_event,
                )
        finally:
            await self._cancel_task(active_task)

    def _start_prefetch_task(
        self,
        chunk_text: str,
        voice: str,
        sampling_template: dict,
        trim_silence: bool,
        prepad_ms: float | None,
        cancel_event: asyncio.Event | None,
    ) -> tuple[asyncio.Queue[bytes | None], asyncio.Task[None]]:
        queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=settings.ws_queue_maxsize)
        prefetcher = ChunkPrefetcher(
            engine=self.engine.engine,
            voice=voice,
            sampling_template=sampling_template,
            trim_silence=trim_silence,
            prepad_ms=prepad_ms,
            cancel_event=cancel_event,
        )
        task = asyncio.create_task(prefetcher.run(chunk_text, queue))
        return queue, task

    async def _await_task(self, task: asyncio.Task[None] | None) -> None:
        if task is None:
            return
        with contextlib.suppress(asyncio.CancelledError):
            await task

    async def _cancel_task(self, task: asyncio.Task[None] | None) -> None:
        if task is None:
            return
        task.cancel()
        await self._await_task(task)

    def _prepare_sampling_params(self, sampling_kwargs: dict | None) -> dict:
        """Normalize and enrich SamplingParams kwargs for streaming."""
        params = dict(sampling_kwargs or {})
        params["temperature"] = float(params.get("temperature", settings.default_temperature))
        params["top_p"] = float(params.get("top_p", settings.default_top_p))
        params["repetition_penalty"] = float(params.get("repetition_penalty", settings.default_repetition_penalty))
        params["max_tokens"] = int(params.get("max_tokens", settings.streaming_default_max_tokens))
        params["stop_token_ids"] = list(settings.streaming_stop_token_ids)
        params["detokenize"] = settings.trt_detokenize
        params["skip_special_tokens"] = settings.trt_skip_special_tokens
        params["add_special_tokens"] = settings.trt_add_special_tokens
        params["ignore_eos"] = settings.trt_ignore_eos
        return params

    @staticmethod
    def _new_sampling_params(template: dict) -> SamplingParams:
        """Instantiate a fresh SamplingParams object for each generation."""
        return SamplingParams(**template)

    @staticmethod
    async def _send_sentence_start(
        ws: Any, sentence_text: str, request_id: str | None, cancel_event: asyncio.Event | None
    ) -> bool:
        if cancel_event is not None and cancel_event.is_set():
            return False
        with contextlib.suppress(Exception):
            payload = {
                settings.ws_key_type: settings.ws_type_sentence,
                settings.ws_key_text: sentence_text,
            }
            if request_id:
                payload[settings.ws_key_request_id] = request_id
            await ws.send_json(payload)
            return True
        return False

    @staticmethod
    async def _send_sentence_end(ws: Any, request_id: str | None, cancel_event: asyncio.Event | None) -> bool:
        if cancel_event is not None and cancel_event.is_set():
            return False
        with contextlib.suppress(Exception):
            payload = {settings.ws_key_type: settings.ws_type_sentence_end}
            if request_id:
                payload[settings.ws_key_request_id] = request_id
            await ws.send_json(payload)
            return True
        return False

    @staticmethod
    async def _send_audio_end(ws: Any, request_id: str | None = None) -> None:
        with contextlib.suppress(Exception):
            payload = {settings.ws_key_type: settings.ws_type_audio_end}
            if request_id:
                payload[settings.ws_key_request_id] = request_id
            await ws.send_json(payload)

    def _resolve_voice(self, voice: str) -> str:
        internal_names = set(getattr(settings, "internal_voice_names", ()))
        if not internal_names and hasattr(settings, "streaming"):
            internal_names = set(getattr(settings.streaming, "internal_voice_names", ()))
        return voice if voice in internal_names else resolve_voice(voice)
