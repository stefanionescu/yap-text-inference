"""Metrics, timing, and result utilities.

This subpackage provides data structures and utilities for tracking
benchmark metrics, TTFB samples, and result formatting.
"""

from .math import round_ms, secs_to_ms
from .results import error_result, result_to_dict, success_result
from .ttfb import create_ttfb_aggregator, emit_ttfb_summary, has_ttfb_samples, record_ttfb

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
]
