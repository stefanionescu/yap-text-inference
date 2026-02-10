"""Tool classifier log noise suppression.

Suppresses verbose output during tool-only deployments including pip install
progress, classifier warmup logs, and deprecation warnings.
"""

from __future__ import annotations

import io
import re
import sys
import logging
from typing import cast
from collections.abc import Iterable

from src.config.filters import TOOL_NOISE_PATTERNS

logger = logging.getLogger("log_filter")

_STATE = {"streams_patched": False}
MIN_ARGS = 2


class ToolNoiseFilterStream:
    """Wraps a stdio stream and drops tool classifier noise.

    Tool-only deployments emit verbose pip install output and classifier
    initialization logs. This stream wrapper intercepts and filters known
    noise patterns.
    """

    def __init__(
        self,
        stream: io.TextIOBase,
        patterns: tuple[re.Pattern[str], ...] = TOOL_NOISE_PATTERNS,
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
        if is_tool_noise(text, self._patterns):
            return
        if newline:
            self._stream.write(f"{text}\n")
        else:
            self._stream.write(text)

    def __getattr__(self, name: str):  # pragma: no cover
        return getattr(self._stream, name)


def is_tool_noise(
    text: str,
    patterns: tuple[re.Pattern[str], ...] = TOOL_NOISE_PATTERNS,
) -> bool:
    """Check if text matches known tool noise patterns."""
    normalized = text.strip()
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in patterns)


def _install_stream_filters() -> None:
    """Install stdout/stderr wrappers that drop tool noise."""
    if _STATE["streams_patched"]:
        return

    try:
        sys.stdout = ToolNoiseFilterStream(cast(io.TextIOBase, sys.stdout), TOOL_NOISE_PATTERNS)
        sys.stderr = ToolNoiseFilterStream(cast(io.TextIOBase, sys.stderr), TOOL_NOISE_PATTERNS)
        if hasattr(sys, "__stdout__") and sys.__stdout__ is not None:
            sys.__stdout__ = ToolNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stdout__),
                TOOL_NOISE_PATTERNS,
            )
        if hasattr(sys, "__stderr__") and sys.__stderr__ is not None:
            sys.__stderr__ = ToolNoiseFilterStream(  # type: ignore[misc,assignment]
                cast(io.TextIOBase, sys.__stderr__),
                TOOL_NOISE_PATTERNS,
            )
        _STATE["streams_patched"] = True
    except Exception as exc:  # pragma: no cover
        logger.debug("failed to wrap stdio for tool log filtering: %s", exc)


def _suppress_tool_loggers() -> None:
    """Set tool-related loggers to WARNING level to reduce noise."""
    for logger_name in (
        "src.classifier",
        "src.classifier.adapter",
        "src.classifier.backend",
        "src.classifier.batch",
    ):
        logging.getLogger(logger_name).setLevel(logging.WARNING)


def configure_tool_logging() -> None:
    """Suppress tool classifier log noise during deployment.

    This configures multiple layers of suppression:
    1. Python loggers set to WARNING level
    2. Stream filters for pip output and deprecation warnings
    """
    _suppress_tool_loggers()
    _install_stream_filters()


def _filter_stdin() -> int:
    """Filter stdin lines, dropping tool noise, and echo the rest."""
    for line in sys.stdin:
        if not is_tool_noise(line):
            sys.stdout.write(line)
            sys.stdout.flush()
    return 0


def main() -> int:
    """CLI entry point for tool log filtering."""
    if len(sys.argv) < MIN_ARGS:
        print("Usage: python -m src.scripts.filters.tool <configure-logging|filter-logs>", file=sys.stderr)
        return 1

    cmd = sys.argv[1]
    if cmd == "configure-logging":
        configure_tool_logging()
        return 0
    if cmd == "filter-logs":
        return _filter_stdin()

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["configure_tool_logging", "ToolNoiseFilterStream", "is_tool_noise", "main"]
