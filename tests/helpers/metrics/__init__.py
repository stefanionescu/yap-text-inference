"""Metrics, timing, and result utilities.

This subpackage provides data structures and utilities for tracking
benchmark metrics, TTFB samples, and result formatting.
"""

from .math import round_ms, secs_to_ms
from .results import error_result, result_to_dict, success_result
from .types import StreamState, TTFBSamples, SessionContext, BenchmarkResultData
from .ttfb import record_ttfb, has_ttfb_samples, emit_ttfb_summary, create_ttfb_aggregator

__all__ = [
    # math
    "round_ms",
    "secs_to_ms",
    # results
    "error_result",
    "result_to_dict",
    "success_result",
    # ttfb
    "create_ttfb_aggregator",
    "emit_ttfb_summary",
    "has_ttfb_samples",
    "record_ttfb",
    # types
    "BenchmarkResultData",
    "SessionContext",
    "StreamState",
    "TTFBSamples",
]

