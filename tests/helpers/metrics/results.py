"""Shared result factories for test utilities.

This module provides factory functions for creating consistent result
dictionaries across all test scripts. Uses BenchmarkResultData from tests.state.
"""

from __future__ import annotations

from typing import Any

from tests.state import BenchmarkResultData


def error_result(
    error: str,
    *,
    phase: int = 1,
    error_code: str | None = None,
    recoverable: bool = False,
) -> dict[str, Any]:
    """Create an error result dict with consistent structure."""
    result: dict[str, Any] = {
        "ok": False,
        "error": error,
        "phase": phase,
    }
    if error_code:
        result["error_code"] = error_code
    if recoverable:
        result["recoverable"] = recoverable
    return result


def success_result(
    *,
    phase: int = 1,
    ttfb_toolcall_ms: float | None = None,
    ttfb_chat_ms: float | None = None,
    first_sentence_ms: float | None = None,
    first_3_words_ms: float | None = None,
) -> dict[str, Any]:
    """Create a success result dict with timing metrics."""
    return {
        "ok": True,
        "phase": phase,
        "ttfb_toolcall_ms": ttfb_toolcall_ms,
        "ttfb_chat_ms": ttfb_chat_ms,
        "first_sentence_ms": first_sentence_ms,
        "first_3_words_ms": first_3_words_ms,
    }


def result_to_dict(data: BenchmarkResultData) -> dict[str, Any]:
    """Convert BenchmarkResultData to a plain dict representation."""
    result: dict[str, Any] = {"ok": data.ok, "phase": data.phase}
    if not data.ok:
        result["error"] = data.error
        if data.error_code:
            result["error_code"] = data.error_code
        result["recoverable"] = data.recoverable
    else:
        if data.ttfb_toolcall_ms is not None:
            result["ttfb_toolcall_ms"] = data.ttfb_toolcall_ms
        if data.ttfb_chat_ms is not None:
            result["ttfb_chat_ms"] = data.ttfb_chat_ms
        if data.first_sentence_ms is not None:
            result["first_sentence_ms"] = data.first_sentence_ms
        if data.first_3_words_ms is not None:
            result["first_3_words_ms"] = data.first_3_words_ms
    return result


__all__ = [
    "error_result",
    "success_result",
    "result_to_dict",
]
