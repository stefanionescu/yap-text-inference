"""Chat streaming controller built on top of vLLM."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import AsyncGenerator, Awaitable, Callable


logger = logging.getLogger(__name__)
STREAM_LABEL = "chat"

CancelCheck = Callable[[], bool | Awaitable[bool]] | None


class StreamCancelledError(Exception):
    """Raised when a cooperative cancel check requests termination."""


@dataclass(slots=True)
class ChatStreamConfig:
    """Configuration for chat streaming."""

    session_id: str
    request_id: str
    prompt: str
    sampling_params: Any
    engine_getter: Callable[[], Awaitable[Any]]
    timeout_s: float
    priority: int = 0
    flush_ms: float = 0.0
    cancel_check: CancelCheck = None


class ChatStreamController:
    """Handles buffering, cancellation, and logging for chat generations."""

    def __init__(self, config: ChatStreamConfig):
        self._cfg = config
        self._full_text: str = ""
        self._ttfb_ms: float | None = None
        self._cancelled = False
        self._buffer: list[str] = []
        self._last_flush_at = time.perf_counter()
        self._start_time: float | None = None

    def __aiter__(self) -> AsyncGenerator[str, None]:
        return self.iter_text()

    async def iter_text(self) -> AsyncGenerator[str, None]:
        start = time.perf_counter()
        cfg = self._cfg
        self._start_time = start
        logger.info(
            "%s_stream: start session_id=%s req_id=%s timeout_s=%.2f flush_ms=%.1f",
            STREAM_LABEL,
            cfg.session_id,
            cfg.request_id,
            cfg.timeout_s,
            cfg.flush_ms,
        )

        try:
            async for out in _stream_with_timeout(
                get_engine=cfg.engine_getter,
                prompt=cfg.prompt,
                sampling_params=cfg.sampling_params,
                request_id=cfg.request_id,
                priority=cfg.priority,
                timeout_s=cfg.timeout_s,
                cancel_check=cfg.cancel_check,
            ):
                delta = self._extract_delta(out)
                if not delta:
                    continue
                for chunk in self._emit(delta):
                    yield chunk
        except StreamCancelledError:
            self._cancelled = True
            logger.info(
                "%s_stream: cancelled session_id=%s req_id=%s",
                STREAM_LABEL,
                cfg.session_id,
                cfg.request_id,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "%s_stream: timeout session_id=%s req_id=%s",
                STREAM_LABEL,
                cfg.session_id,
                cfg.request_id,
            )
            raise
        finally:
            if not self._cancelled:
                tail = self._flush_tail()
                if tail:
                    yield tail
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            logger.info(
                "%s_stream: end session_id=%s req_id=%s total_len=%s ms=%.1f",
                STREAM_LABEL,
                cfg.session_id,
                cfg.request_id,
                len(self._full_text),
                elapsed_ms,
            )

    @property
    def full_text(self) -> str:
        return self._full_text

    @property
    def was_cancelled(self) -> bool:
        return self._cancelled

    @property
    def ttfb_ms(self) -> float | None:
        return self._ttfb_ms

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _extract_delta(self, output: Any) -> str:
        if not getattr(output, "outputs", None):
            return ""
        text = output.outputs[0].text
        if not isinstance(text, str):
            return ""
        if not text.startswith(self._full_text):
            # Unexpected reset; fall back to newest text.
            delta = text
        else:
            delta = text[len(self._full_text):]
        if not delta:
            return ""
        self._full_text = text
        if self._ttfb_ms is None:
            self._ttfb_ms = 0.0  # marker set; actual value computed on emit
        return delta

    def _emit(self, delta: str) -> list[str]:
        cfg = self._cfg
        if cfg.flush_ms <= 0:
            self._record_ttfb_if_needed()
            return [delta]

        self._buffer.append(delta)
        now = time.perf_counter()
        should_flush = (now - self._last_flush_at) * 1000.0 >= cfg.flush_ms
        if not should_flush:
            return []

        chunk = "".join(self._buffer)
        self._buffer.clear()
        self._last_flush_at = now
        self._record_ttfb_if_needed()
        return [chunk]

    def _flush_tail(self) -> str:
        if self._cfg.flush_ms <= 0 or not self._buffer:
            return ""
        chunk = "".join(self._buffer)
        self._buffer.clear()
        return chunk

    def _record_ttfb_if_needed(self) -> None:
        if self._ttfb_ms == 0.0:
            if self._start_time is None:
                return
            self._ttfb_ms = (time.perf_counter() - self._start_time) * 1000.0
            cfg = self._cfg
            logger.info(
                "%s_stream: first token session_id=%s req_id=%s ttfb_ms=%.1f",
                STREAM_LABEL,
                cfg.session_id,
                cfg.request_id,
                self._ttfb_ms,
            )


async def _stream_with_timeout(
    get_engine: Callable[[], Awaitable[Any]],
    prompt: str,
    sampling_params: Any,
    request_id: str,
    priority: int,
    timeout_s: float,
    cancel_check: CancelCheck = None,
) -> AsyncGenerator[Any, None]:
    engine = await get_engine()
    stream = engine.generate(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
        priority=priority,
    )
    cancel_checker = _CancelChecker(cancel_check)

    try:
        async with asyncio.timeout(timeout_s):
            async for out in stream:
                if await cancel_checker.triggered():
                    await _abort(engine, request_id)
                    raise StreamCancelledError()
                yield out
    except asyncio.TimeoutError:
        await _abort(engine, request_id)
        raise


async def _abort(engine: Any, request_id: str) -> None:
    with contextlib.suppress(Exception):
        await engine.abort(request_id)


class _CancelChecker:
    def __init__(self, cancel_check: CancelCheck):
        self._check = cancel_check

    async def triggered(self) -> bool:
        if self._check is None:
            return False
        result = self._check()
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)


__all__ = [
    "ChatStreamConfig",
    "ChatStreamController",
    "StreamCancelledError",
]
