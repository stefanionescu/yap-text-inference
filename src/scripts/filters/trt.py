"""TensorRT-LLM log noise suppression.

Suppresses verbose TensorRT-LLM and modelopt output during quantization.
Uses stream filtering to catch C++ output that bypasses Python logging.
"""

from __future__ import annotations

import io
import logging
import os
import re
import sys
import warnings
from collections.abc import Iterable

from src.config.filters import TRTLLM_NOISE_PATTERNS

logger = logging.getLogger("log_filter")

# Track whether streams have been patched to avoid double-patching
_STREAMS_PATCHED = False


class NoiseFilterStream:
    """Wraps a stdio stream and drops known TRT-LLM noise lines.

    TensorRT-LLM and modelopt emit verbose output directly to stdout/stderr,
    bypassing Python's logging system. This stream wrapper intercepts that
    output and filters known noise patterns.
    """

    def __init__(
        self,
        stream: io.TextIOBase,
        patterns: tuple[re.Pattern[str], ...] = TRTLLM_NOISE_PATTERNS,
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
        if is_trt_noise(text, self._patterns):
            return
        if newline:
            self._stream.write(f"{text}\n")
        else:
            self._stream.write(text)

    def __getattr__(self, name: str):  # pragma: no cover
        return getattr(self._stream, name)


def is_trt_noise(
    text: str,
    patterns: tuple[re.Pattern[str], ...] = TRTLLM_NOISE_PATTERNS,
) -> bool:
    """Check if text matches known TRT-LLM noise patterns."""
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in patterns)


def _install_stream_filters() -> None:
    """Install stdout/stderr wrappers that drop common TRT-LLM noise."""
    global _STREAMS_PATCHED
    if _STREAMS_PATCHED:
        return

    try:
        sys.stdout = NoiseFilterStream(sys.stdout, TRTLLM_NOISE_PATTERNS)
        sys.stderr = NoiseFilterStream(sys.stderr, TRTLLM_NOISE_PATTERNS)
        # Also wrap __stdout__/__stderr__ in case libraries use them directly
        if hasattr(sys, "__stdout__") and sys.__stdout__ is not None:
            sys.__stdout__ = NoiseFilterStream(sys.__stdout__, TRTLLM_NOISE_PATTERNS)
        if hasattr(sys, "__stderr__") and sys.__stderr__ is not None:
            sys.__stderr__ = NoiseFilterStream(sys.__stderr__, TRTLLM_NOISE_PATTERNS)
        _STREAMS_PATCHED = True
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to wrap stdio for TRT log filtering: %s", exc)


def _suppress_loggers() -> None:
    """Set TensorRT-LLM and modelopt loggers to ERROR level."""
    for logger_name in (
        "tensorrt_llm",
        "tensorrt_llm.logger",
        "tensorrt_llm.runtime",
        "modelopt",
        "modelopt.torch",
        "modelopt.torch.quantization",
        "nvidia_modelopt",
        "accelerate",
    ):
        logging.getLogger(logger_name).setLevel(logging.ERROR)


def _suppress_warnings() -> None:
    """Suppress deprecation warnings from torch/modelopt."""
    warnings.filterwarnings("ignore", message=r".*`?torch_dtype`?.*deprecated.*")
    warnings.filterwarnings("ignore", message=r".*`?dtype`?.*instead.*")
    warnings.filterwarnings("ignore", message=".*Python version.*below the recommended.*")
    warnings.filterwarnings("ignore", category=DeprecationWarning, module="modelopt")
    warnings.filterwarnings("ignore", category=FutureWarning, module="modelopt")


def _suppress_datasets_progress() -> None:
    """Suppress datasets library progress bars."""
    try:
        from datasets import disable_progress_bars as datasets_disable_progress
        datasets_disable_progress()
    except Exception:
        pass


def configure_trt_logging() -> None:
    """Suppress TensorRT-LLM and modelopt log noise during quantization.

    This configures multiple layers of suppression:
    1. Python loggers set to ERROR level
    2. Warning filters for deprecation noise
    3. Environment variables for TRT-LLM and tqdm
    4. Stream filters for C++ output
    """
    _suppress_loggers()
    _suppress_warnings()

    # Suppress TensorRT-LLM version banner via environment
    os.environ.setdefault("TRTLLM_LOG_LEVEL", "error")

    # Suppress datasets progress bars
    _suppress_datasets_progress()

    # Suppress tqdm progress bars globally for quantization
    os.environ.setdefault("TQDM_DISABLE", "1")

    # Install stream filters last (they wrap stdout/stderr)
    _install_stream_filters()


__all__ = ["configure_trt_logging", "NoiseFilterStream", "is_trt_noise"]

