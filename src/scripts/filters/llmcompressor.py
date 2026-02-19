"""LLMCompressor/AutoAWQ log filtering.

Suppresses calibration and quantization progress bars emitted by llmcompressor
and AutoAWQ during AWQ/GPTQ quantization. Uses stream filtering to catch
tqdm output that bypasses Python logging.
"""

from __future__ import annotations

import io
import os
import re
import sys
import logging
from typing import cast
from collections.abc import Iterable

from src.config.filters import LLMCOMPRESSOR_NOISE_PATTERNS

logger = logging.getLogger("log_filter")

_STATE = {"streams_patched": False}


class LLMCompressorNoiseFilterStream:
    """Wraps a stdio stream and drops llmcompressor/AutoAWQ calibration noise.

    LLMCompressor and AutoAWQ emit verbose tqdm progress bars directly to
    stdout/stderr during calibration. This stream wrapper intercepts that
    output and filters known noise patterns.
    """

    def __init__(
        self,
        stream: io.TextIOBase,
        patterns: tuple[re.Pattern[str], ...] = LLMCOMPRESSOR_NOISE_PATTERNS,
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
        if is_llmcompressor_noise(text, self._patterns):
            return
        if newline:
            self._stream.write(f"{text}\n")
        else:
            self._stream.write(text)

    def __getattr__(self, name: str):  # pragma: no cover
        return getattr(self._stream, name)


def _install_stream_filters() -> None:
    """Install stdout/stderr wrappers that drop llmcompressor noise."""
    if _STATE["streams_patched"]:
        return

    try:
        sys.stdout = LLMCompressorNoiseFilterStream(cast(io.TextIOBase, sys.stdout), LLMCOMPRESSOR_NOISE_PATTERNS)
        sys.stderr = LLMCompressorNoiseFilterStream(cast(io.TextIOBase, sys.stderr), LLMCOMPRESSOR_NOISE_PATTERNS)
        if hasattr(sys, "__stdout__") and sys.__stdout__ is not None:
            sys.__stdout__ = LLMCompressorNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stdout__),
                LLMCOMPRESSOR_NOISE_PATTERNS,
            )
        if hasattr(sys, "__stderr__") and sys.__stderr__ is not None:
            sys.__stderr__ = LLMCompressorNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stderr__),
                LLMCOMPRESSOR_NOISE_PATTERNS,
            )
        _STATE["streams_patched"] = True
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to wrap stdio for llmcompressor log filtering: %s", exc)


def _suppress_llmcompressor_loggers() -> None:
    """Set llmcompressor and AutoAWQ loggers to ERROR level."""
    for logger_name in (
        "llmcompressor",
        "llmcompressor.pytorch",
        "llmcompressor.transformers",
        "awq",
        "auto_awq",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)


def _suppress_llmcompressor_tqdm() -> None:
    """Suppress tqdm progress bars used by llmcompressor."""
    os.environ.setdefault("TQDM_DISABLE", "1")


def is_llmcompressor_noise(
    text: str,
    patterns: tuple[re.Pattern[str], ...] = LLMCOMPRESSOR_NOISE_PATTERNS,
) -> bool:
    """Check if text matches known llmcompressor/AutoAWQ noise patterns."""
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in patterns)


def configure_llmcompressor_logging() -> None:
    """Suppress llmcompressor and AutoAWQ log noise during quantization.

    This configures multiple layers of suppression:
    1. Python loggers set to ERROR level
    2. Environment variables for tqdm suppression
    3. Stream filters for tqdm output
    """
    _suppress_llmcompressor_loggers()
    _suppress_llmcompressor_tqdm()
    _install_stream_filters()


__all__ = [
    "configure_llmcompressor_logging",
    "LLMCompressorNoiseFilterStream",
    "is_llmcompressor_noise",
]
