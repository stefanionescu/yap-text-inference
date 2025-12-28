"""Chat streaming controller - engine agnostic.

This module provides the ChatStreamController, which handles the mechanics
of streaming text generation from any engine implementing BaseEngine.

Key Features:

1. Engine Abstraction:
   - Works with both vLLM and TensorRT-LLM
   - Accepts an engine getter function for lazy initialization

2. Micro-Buffering:
   - Accumulates small chunks for flush_ms duration
   - Reduces WebSocket message overhead
   - Configurable via flush_ms (0 = no buffering)

3. Timeout Handling:
   - Generation timeout with async context manager
   - Automatic request abortion on timeout
   - TimeoutError propagation for caller handling

4. Cancellation Support:
   - Cooperative cancellation via cancel_check callback
   - StreamCancelledError for clean termination
   - Automatic request abortion on cancel

5. Telemetry:
   - TTFB (Time To First Byte) tracking
   - Total generation time logging
   - Per-request logging with session/request IDs

Works with both vLLM and TensorRT-LLM engines through the BaseEngine interface.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any
from collections.abc import AsyncGenerator, Awaitable, Callable

from ...engines.base import BaseEngine
from ...helpers.async_compat import timeout as async_timeout

logger = logging.getLogger(__name__)
STREAM_LABEL = "chat"  # Log prefix for chat streams

# Type for cancellation check callbacks
CancelCheck = Callable[[], bool | Awaitable[bool]] | None


class StreamCancelledError(Exception):
    """Raised when a cooperative cancel check requests termination.
    
    This exception is used for clean stream termination when the
    cancel_check callback returns True. It allows callers to
    distinguish cancellation from other errors.
    """


@dataclass(slots=True)
class ChatStreamConfig:
    """Configuration for chat streaming.
    
    Attributes:
        session_id: Session identifier for logging.
        request_id: Unique request ID for tracking and abortion.
        prompt: The formatted prompt to generate from.
        sampling_params: Engine-specific sampling parameters.
        engine_getter: Async function returning the engine instance.
        timeout_s: Maximum seconds for generation.
        flush_ms: Minimum milliseconds between buffer flushes.
        cancel_check: Optional callback to check for cancellation.
    """

    session_id: str
    request_id: str
    prompt: str
    sampling_params: Any
    engine_getter: Callable[[], Awaitable[BaseEngine]]
    timeout_s: float
    flush_ms: float = 0.0
    cancel_check: CancelCheck = None


class ChatStreamController:
    """Handles buffering, cancellation, and logging for chat generations.
    
    This controller provides a clean async iterator interface over engine
    generation streams, adding:
    - Micro-buffering for reduced message overhead
    - Timeout enforcement with automatic abortion
    - Cancellation support via callback
    - TTFB and completion telemetry
    
    Works with any engine implementing the BaseEngine interface,
    including both vLLM and TensorRT-LLM.
    
    Usage:
        config = ChatStreamConfig(...)
        controller = ChatStreamController(config)
        async for chunk in controller:
            process(chunk)
    """

    def __init__(self, config: ChatStreamConfig):
        """Initialize the stream controller.
        
        Args:
            config: ChatStreamConfig with all stream parameters.
        """
        self._cfg = config
        self._full_text: str = ""  # Cumulative generated text
        self._ttfb_ms: float | None = None  # Time to first byte
        self._cancelled = False  # Was stream cancelled?
        self._buffer: list[str] = []  # Micro-buffering accumulator
        self._last_flush_at = time.perf_counter()  # Last buffer flush time
        self._start_time: float | None = None  # Stream start time

    def __aiter__(self) -> AsyncGenerator[str, None]:
        """Enable async iteration: `async for chunk in controller`."""
        return self.iter_text()

    async def iter_text(self) -> AsyncGenerator[str, None]:
        """Main streaming loop with buffering, timeout, and cancellation.
        
        Yields:
            Text chunks (possibly buffered based on flush_ms).
            
        Raises:
            asyncio.TimeoutError: If generation exceeds timeout_s.
            StreamCancelledError: If cancel_check returns True.
        """
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

    def _extract_delta(self, output: Any) -> str:
        """Extract new text delta from engine output.
        
        Works with both EngineOutput (unified format) and raw vLLM output.
        """
        if not hasattr(output, "text") or not isinstance(output.text, str):
            return ""
        text = output.text
        
        if not text.startswith(self._full_text):
            delta = text
        else:
            delta = text[len(self._full_text):]
        if not delta:
            return ""
        self._full_text = text
        if self._ttfb_ms is None:
            self._ttfb_ms = 0.0
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
    get_engine: Callable[[], Awaitable[BaseEngine]],
    prompt: str,
    sampling_params: Any,
    request_id: str,
    timeout_s: float,
    cancel_check: CancelCheck = None,
) -> AsyncGenerator[Any, None]:
    """Stream generation with timeout and cancellation support."""
    engine = await get_engine()
    stream = engine.generate_stream(
        prompt=prompt,
        sampling_params=sampling_params,
        request_id=request_id,
    )
    cancel_checker = _CancelChecker(cancel_check)

    try:
        async with async_timeout(timeout_s):
            async for out in stream:
                if await cancel_checker.triggered():
                    await engine.abort(request_id)
                    raise StreamCancelledError()
                yield out
    except asyncio.TimeoutError:
        await engine.abort(request_id)
        raise


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
