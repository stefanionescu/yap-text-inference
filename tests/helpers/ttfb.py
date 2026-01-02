"""Time-to-first-byte aggregation utilities.

This module provides functions for accumulating TTFB samples and computing
summary statistics (p50, p90, p95). Uses TTFBSamples from types.py for data.
"""

from __future__ import annotations

import math
from typing import Any
from collections.abc import Callable, Mapping, Sequence

from .fmt import section_header, bold, dim
from .types import TTFBSamples


# ============================================================================
# Internal Helpers
# ============================================================================


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


def _format_stats_line(
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


def _emit_first_message(samples: TTFBSamples, sink: Callable[[str], None]) -> None:
    """Emit first message latency (includes prefill overhead)."""
    parts = [f"  {bold('FIRST')}  {dim('(includes prefill)')}"]
    
    if samples.chat_samples:
        parts.append(f"ttfb={_format_ms(samples.chat_samples[0])}")
    if samples.first_3_words_samples:
        parts.append(f"3w={_format_ms(samples.first_3_words_samples[0])}")
    if samples.first_sentence_samples:
        parts.append(f"sent={_format_ms(samples.first_sentence_samples[0])}")
    if samples.tool_samples:
        parts.append(f"tool={_format_ms(samples.tool_samples[0])}")
    
    sink("  ".join(parts))


def _emit_remaining_stats(samples: TTFBSamples, sink: Callable[[str], None]) -> None:
    """Emit statistics for messages after the first."""
    metrics = [
        ("TTFB", samples.chat_samples[1:]),
        ("3-WORDS", samples.first_3_words_samples[1:] if len(samples.first_3_words_samples) > 1 else []),
        ("SENTENCE", samples.first_sentence_samples[1:] if len(samples.first_sentence_samples) > 1 else []),
        ("TOOL", samples.tool_samples[1:] if len(samples.tool_samples) > 1 else []),
    ]
    
    for label, sample_list in metrics:
        if not sample_list:
            continue
        stats = _build_stats(sample_list)
        sink(_format_stats_line(label, stats))


def _emit_single_stats(samples: TTFBSamples, sink: Callable[[str], None]) -> None:
    """Emit stats when we only have a single sample."""
    metrics = [
        ("TTFB", samples.chat_samples),
        ("3-WORDS", samples.first_3_words_samples),
        ("SENTENCE", samples.first_sentence_samples),
        ("TOOL", samples.tool_samples),
    ]
    
    for label, sample_list in metrics:
        if not sample_list:
            continue
        stats = _build_stats(sample_list)
        sink(_format_stats_line(label, stats, show_first=True))


# ============================================================================
# Public Functions
# ============================================================================


def create_ttfb_aggregator() -> TTFBSamples:
    """Create a new TTFB sample aggregator."""
    return TTFBSamples()


def record_ttfb(samples: TTFBSamples, metrics: Mapping[str, Any]) -> None:
    """Record latency values from a metrics dict."""
    tool = _coerce(metrics.get("ttfb_toolcall_ms"))
    chat = _coerce(metrics.get("ttfb_chat_ms"))
    first_3 = _coerce(metrics.get("time_to_first_3_words_ms"))
    first_sent = _coerce(metrics.get("time_to_first_complete_sentence_ms"))
    
    if tool is not None:
        samples.tool_samples.append(tool)
    if chat is not None:
        samples.chat_samples.append(chat)
    if first_3 is not None:
        samples.first_3_words_samples.append(first_3)
    if first_sent is not None:
        samples.first_sentence_samples.append(first_sent)


def has_ttfb_samples(samples: TTFBSamples) -> bool:
    """Return True if any samples have been recorded."""
    return bool(
        samples.tool_samples or 
        samples.chat_samples or 
        samples.first_3_words_samples or 
        samples.first_sentence_samples
    )


def emit_ttfb_summary(samples: TTFBSamples, sink: Callable[[str], None]) -> None:
    """Emit summary statistics with first message separated."""
    sink(section_header("LATENCY SUMMARY"))
    
    has_multi = len(samples.chat_samples) > 1
    
    if has_multi:
        _emit_first_message(samples, sink)
        sink("")
        _emit_remaining_stats(samples, sink)
    else:
        _emit_single_stats(samples, sink)


__all__ = [
    "create_ttfb_aggregator",
    "record_ttfb",
    "has_ttfb_samples",
    "emit_ttfb_summary",
]
