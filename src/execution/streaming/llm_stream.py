"""Shared LLM streaming controller for chat and tool executions."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import Awaitable, Callable
from collections.abc import AsyncGenerator

from .streaming_utils import CancelCheck, StreamCancelledError, stream_with_timeout


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class LLMStreamConfig:
    """Configuration for an LLM streaming request."""

    name: str
    session_id: str
    request_id: str
    prompt: str
    sampling_params: Any
    engine_getter: Callable[[], Awaitable[Any]]
    timeout_s: float
    priority: int = 0
    flush_ms: float = 0.0
    cancel_check: CancelCheck = None


class LLMStream:
    """Unified streaming helper that handles buffering, cancellation, and logging."""

    def __init__(self, config: LLMStreamConfig):
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
            cfg.name,
            cfg.session_id,
            cfg.request_id,
            cfg.timeout_s,
            cfg.flush_ms,
        )

        try:
            async for out in stream_with_timeout(
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
                cfg.name,
                cfg.session_id,
                cfg.request_id,
            )
        except asyncio.TimeoutError:
            logger.warning(
                "%s_stream: timeout session_id=%s req_id=%s",
                cfg.name,
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
                cfg.name,
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
                cfg.name,
                cfg.session_id,
                cfg.request_id,
                self._ttfb_ms,
            )

