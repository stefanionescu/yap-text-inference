"""Time-to-first-byte aggregation utilities.

This module provides the TTFBAggregator class that accumulates TTFB samples
across multiple requests and computes summary statistics (p50, p90, p95).
Used by warmup and conversation tests to report latency metrics.

For multi-turn conversation tests, the first message latency is reported
separately since it includes prefill overhead for system prompt and history.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Callable, Mapping, Sequence

from tests.helpers.fmt import section_header, bold, dim, yellow


def _percentile(samples: Sequence[float], frac: float) -> float:
    """Compute the given percentile (0-1) from sorted samples."""
    if not samples:
        raise ValueError("percentile requires at least one sample")
    if frac <= 0:
        return min(samples)
    if frac >= 1:
        return max(samples)
    ordered = sorted(samples)
    position = frac * (len(ordered) - 1)
    lower_idx = math.floor(position)
    upper_idx = math.ceil(position)
    if lower_idx == upper_idx:
        return ordered[lower_idx]
    weight = position - lower_idx
    return ordered[lower_idx] + (ordered[upper_idx] - ordered[lower_idx]) * weight


def _coerce(value: Any) -> float | None:
    """Coerce a value to float or return None."""
    if value is None:
        return None
    return float(value)


def _build_stats(samples: Sequence[float]) -> dict[str, float | int]:
    """Build a stats dict from a sequence of samples."""
    count = len(samples)
    return {
        "count": count,
        "first": samples[0] if samples else 0,
        "average": sum(samples) / count if count else 0,
        "p50": _percentile(samples, 0.50) if samples else 0,
        "p90": _percentile(samples, 0.90) if samples else 0,
        "p95": _percentile(samples, 0.95) if samples else 0,
    }


def _format_ms(value: float | None) -> str:
    """Format milliseconds value."""
    if value is None:
        return "—"
    return f"{value:.0f}ms"


@dataclass
class TTFBAggregator:
    """Accumulates TTFB and latency samples, reports summary statistics.
    
    For multi-turn tests, separates first message (which includes prefill
    overhead) from subsequent messages in the statistics.
    """

    # TTFB samples
    tool_samples: list[float] = field(default_factory=list)
    chat_samples: list[float] = field(default_factory=list)
    
    # Additional latency samples
    first_3_words_samples: list[float] = field(default_factory=list)
    first_sentence_samples: list[float] = field(default_factory=list)

    def record(self, metrics: Mapping[str, Any]) -> None:
        """Record latency values from a metrics dict."""
        tool = _coerce(metrics.get("ttfb_toolcall_ms"))
        chat = _coerce(metrics.get("ttfb_chat_ms"))
        first_3 = _coerce(metrics.get("time_to_first_3_words_ms"))
        first_sent = _coerce(metrics.get("time_to_first_complete_sentence_ms"))
        
        if tool is not None:
            self.tool_samples.append(tool)
        if chat is not None:
            self.chat_samples.append(chat)
        if first_3 is not None:
            self.first_3_words_samples.append(first_3)
        if first_sent is not None:
            self.first_sentence_samples.append(first_sent)

    def has_samples(self) -> bool:
        """Return True if any samples have been recorded."""
        return bool(
            self.tool_samples or 
            self.chat_samples or 
            self.first_3_words_samples or 
            self.first_sentence_samples
        )

    def emit(self, sink: Callable[[str], None]) -> None:
        """Emit summary statistics with first message separated.
        
        For multi-turn tests, shows:
        - First message latencies (includes prefill overhead)
        - Remaining messages: avg, p50, p90, p95 (excludes first)
        """
        sink(section_header("LATENCY SUMMARY"))
        
        # Determine if we have multi-turn data (more than 1 sample)
        has_multi = len(self.chat_samples) > 1
        
        if has_multi:
            # Print first message stats
            self._emit_first_message(sink)
            sink("")  # blank line
            # Print remaining stats (excluding first)
            self._emit_remaining_stats(sink)
        else:
            # Single sample - just print what we have
            self._emit_single_stats(sink)
    
    def _emit_first_message(self, sink: Callable[[str], None]) -> None:
        """Emit first message latency (includes prefill overhead)."""
        parts = [f"  {bold('FIRST')}  {dim('(includes prefill)')}"]
        
        if self.chat_samples:
            parts.append(f"ttfb={_format_ms(self.chat_samples[0])}")
        if self.first_3_words_samples:
            parts.append(f"3w={_format_ms(self.first_3_words_samples[0])}")
        if self.first_sentence_samples:
            parts.append(f"sent={_format_ms(self.first_sentence_samples[0])}")
        if self.tool_samples:
            parts.append(f"tool={_format_ms(self.tool_samples[0])}")
        
        sink("  ".join(parts))
    
    def _emit_remaining_stats(self, sink: Callable[[str], None]) -> None:
        """Emit statistics for messages after the first (excludes prefill overhead)."""
        metrics = [
            ("TTFB", self.chat_samples[1:]),
            ("3-WORDS", self.first_3_words_samples[1:] if len(self.first_3_words_samples) > 1 else []),
            ("SENTENCE", self.first_sentence_samples[1:] if len(self.first_sentence_samples) > 1 else []),
            ("TOOL", self.tool_samples[1:] if len(self.tool_samples) > 1 else []),
        ]
        
        for label, samples in metrics:
            if not samples:
                continue
            stats = _build_stats(samples)
            sink(self._format_stats_line(label, stats))
    
    def _emit_single_stats(self, sink: Callable[[str], None]) -> None:
        """Emit stats when we only have a single sample."""
        metrics = [
            ("TTFB", self.chat_samples),
            ("3-WORDS", self.first_3_words_samples),
            ("SENTENCE", self.first_sentence_samples),
            ("TOOL", self.tool_samples),
        ]
        
        for label, samples in metrics:
            if not samples:
                continue
            stats = _build_stats(samples)
            sink(self._format_stats_line(label, stats, show_first=True))
    
    def _format_stats_line(
        self, 
        label: str, 
        stats: dict[str, float | int],
        show_first: bool = False,
    ) -> str:
        """Format a stats line for a metric."""
        parts = [f"  {bold(label):>10}"]
        
        if show_first:
            parts.append(f"first={stats['first']:>6.0f}ms")
        
        parts.extend([
            f"avg={stats['average']:>6.0f}ms",
            f"p50={stats['p50']:>6.0f}ms",
            f"p90={stats['p90']:>6.0f}ms",
            f"p95={stats['p95']:>6.0f}ms",
            dim(f"(n={stats['count']})"),
        ])
        
        return "  ".join(parts)


__all__ = ["TTFBAggregator"]
