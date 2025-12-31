"""Shared result factories for test utilities.

This module provides factory functions for creating consistent result
dictionaries across all test scripts. Previously, error dicts like
{"ok": False, "error": ..., "phase": ...} were duplicated inline.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class BenchmarkResult:
    """Result of a single benchmark transaction.
    
    Attributes:
        ok: True if the transaction completed successfully.
        phase: Which phase of a multi-phase transaction (1 or 2).
        error: Error message if ok is False.
        ttfb_toolcall_ms: Time to first toolcall frame in milliseconds.
        ttfb_chat_ms: Time to first chat token in milliseconds.
        first_sentence_ms: Time to first complete sentence.
        first_3_words_ms: Time to first 3 words.
    """

    ok: bool
    phase: int = 1
    error: str | None = None
    error_code: str | None = None
    recoverable: bool = False
    ttfb_toolcall_ms: float | None = None
    ttfb_chat_ms: float | None = None
    first_sentence_ms: float | None = None
    first_3_words_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for backwards compatibility with existing code."""
        result: dict[str, Any] = {"ok": self.ok, "phase": self.phase}
        if not self.ok:
            result["error"] = self.error
            if self.error_code:
                result["error_code"] = self.error_code
            result["recoverable"] = self.recoverable
        else:
            if self.ttfb_toolcall_ms is not None:
                result["ttfb_toolcall_ms"] = self.ttfb_toolcall_ms
            if self.ttfb_chat_ms is not None:
                result["ttfb_chat_ms"] = self.ttfb_chat_ms
            if self.first_sentence_ms is not None:
                result["first_sentence_ms"] = self.first_sentence_ms
            if self.first_3_words_ms is not None:
                result["first_3_words_ms"] = self.first_3_words_ms
        return result


def error_result(
    error: str,
    *,
    phase: int = 1,
    error_code: str | None = None,
    recoverable: bool = False,
) -> dict[str, Any]:
    """Create an error result dict with consistent structure.
    
    Args:
        error: Human-readable error message.
        phase: Phase number for multi-phase transactions.
        error_code: Machine-readable error code if available.
        recoverable: Whether the error is recoverable.
    
    Returns:
        Dict with ok=False and error details.
    """
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
    """Create a success result dict with timing metrics.
    
    Args:
        phase: Phase number for multi-phase transactions.
        ttfb_toolcall_ms: Time to first toolcall frame.
        ttfb_chat_ms: Time to first chat token.
        first_sentence_ms: Time to first complete sentence.
        first_3_words_ms: Time to first 3 words.
    
    Returns:
        Dict with ok=True and timing metrics.
    """
    return {
        "ok": True,
        "phase": phase,
        "ttfb_toolcall_ms": ttfb_toolcall_ms,
        "ttfb_chat_ms": ttfb_chat_ms,
        "first_sentence_ms": first_sentence_ms,
        "first_3_words_ms": first_3_words_ms,
    }


__all__ = [
    "BenchmarkResult",
    "error_result",
    "success_result",
]

