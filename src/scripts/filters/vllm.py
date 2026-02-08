"""vLLM log noise suppression.

Suppresses verbose vLLM engine initialization output during startup.
Uses stream filtering to catch worker process output and progress bars.
"""

from __future__ import annotations

import io
import os
import re
import sys
import logging
import contextlib
from typing import cast
from collections.abc import Iterable

from src.config.filters import VLLM_NOISE_PATTERNS

logger = logging.getLogger("log_filter")

_STATE = {"streams_patched": False}


class VLLMNoiseFilterStream:
    """Wraps a stdio stream and drops vLLM engine initialization noise.

    vLLM emits verbose logs during engine startup including worker process
    output, CUDA graph compilation progress, and model loading status.
    This stream wrapper intercepts and filters known noise patterns.
    """

    def __init__(
        self,
        stream: io.TextIOBase,
        patterns: tuple[re.Pattern[str], ...] = VLLM_NOISE_PATTERNS,
    ):
        super().__init__()
        self._stream = stream
        self._patterns = patterns
        self._buffer = ""

    def write(self, text: str) -> int:
        if not isinstance(text, str):
            text = str(text)
        length = len(text)
        if not text:
            return 0
        self._buffer += text
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._emit(line, newline=True)
        return length

    def writelines(self, lines: Iterable[str]) -> None:
        for line in lines:
            self.write(line)

    def flush(self) -> None:
        if self._buffer:
            self._emit(self._buffer, newline=False)
            self._buffer = ""
        self._stream.flush()

    def _emit(self, text: str, newline: bool) -> None:
        if not text and newline:
            self._stream.write("\n")
            return
        if is_vllm_noise(text, self._patterns):
            return
        if newline:
            self._stream.write(f"{text}\n")
        else:
            self._stream.write(text)

    def __getattr__(self, name: str):  # pragma: no cover
        return getattr(self._stream, name)


def is_vllm_noise(
    text: str,
    patterns: tuple[re.Pattern[str], ...] = VLLM_NOISE_PATTERNS,
) -> bool:
    """Check if text matches known vLLM noise patterns."""
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in patterns)


def _install_stream_filters() -> None:
    """Install stdout/stderr wrappers that drop vLLM noise."""
    if _STATE["streams_patched"]:
        return

    try:
        sys.stdout = VLLMNoiseFilterStream(cast(io.TextIOBase, sys.stdout), VLLM_NOISE_PATTERNS)
        sys.stderr = VLLMNoiseFilterStream(cast(io.TextIOBase, sys.stderr), VLLM_NOISE_PATTERNS)
        if hasattr(sys, "__stdout__") and sys.__stdout__ is not None:
            sys.__stdout__ = VLLMNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stdout__),
                VLLM_NOISE_PATTERNS,
            )
        if hasattr(sys, "__stderr__") and sys.__stderr__ is not None:
            sys.__stderr__ = VLLMNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stderr__),
                VLLM_NOISE_PATTERNS,
            )
        _STATE["streams_patched"] = True
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to wrap stdio for vLLM log filtering: %s", exc)


def _suppress_vllm_loggers() -> None:
    """Set vLLM loggers to ERROR level."""
    for logger_name in (
        "vllm",
        "vllm.config",
        "vllm.engine",
        "vllm.executor",
        "vllm.worker",
        "vllm.model_executor",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)


def configure_vllm_logging() -> None:
    """Suppress vLLM log noise during engine initialization.

    This configures multiple layers of suppression:
    1. Python loggers set to ERROR level
    2. Stream filters for worker process output and progress bars
    """
    _suppress_vllm_loggers()
    _install_stream_filters()


class SuppressedFDContext:
    """Context manager that suppresses C++ stdout/stderr by redirecting file descriptors.

    This is necessary because vLLM worker processes write directly to file
    descriptors, bypassing Python's sys.stdout/stderr wrappers.

    When file descriptors are redirected before spawning workers, the workers
    inherit the redirected fds and their output is also suppressed.
    """

    def __init__(self, suppress_stdout: bool = True, suppress_stderr: bool = True):
        self._suppress_stdout = suppress_stdout
        self._suppress_stderr = suppress_stderr
        self._saved_stdout_fd: int | None = None
        self._saved_stderr_fd: int | None = None
        self._devnull: int | None = None

    def __enter__(self) -> SuppressedFDContext:
        # Flush all Python and C stdio buffers before redirecting
        sys.stdout.flush()
        sys.stderr.flush()
        with contextlib.suppress(Exception):
            import ctypes  # noqa: PLC0415

            libc = ctypes.CDLL(None)
            libc.fflush(None)  # Flush all C stdio streams

        self._devnull = os.open(os.devnull, os.O_WRONLY)

        if self._suppress_stdout:
            self._saved_stdout_fd = os.dup(1)
            os.dup2(self._devnull, 1)

        if self._suppress_stderr:
            self._saved_stderr_fd = os.dup(2)
            os.dup2(self._devnull, 2)

        return self

    def __exit__(self, *args) -> None:
        # Flush any remaining output before restoring
        with contextlib.suppress(Exception):
            import ctypes  # noqa: PLC0415

            libc = ctypes.CDLL(None)
            libc.fflush(None)

        sys.stdout.flush()
        sys.stderr.flush()

        if self._saved_stdout_fd is not None:
            os.dup2(self._saved_stdout_fd, 1)
            os.close(self._saved_stdout_fd)

        if self._saved_stderr_fd is not None:
            os.dup2(self._saved_stderr_fd, 2)
            os.close(self._saved_stderr_fd)

        if self._devnull is not None:
            os.close(self._devnull)


__all__ = ["configure_vllm_logging", "SuppressedFDContext", "VLLMNoiseFilterStream", "is_vllm_noise"]
