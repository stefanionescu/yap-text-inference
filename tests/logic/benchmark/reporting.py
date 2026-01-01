"""Benchmark reporting with clean, consistent formatting.

Provides summary output for benchmark runs including latency percentiles,
error breakdown, and phase-separated metrics for double-ttfb mode.
"""

from __future__ import annotations

import os
from typing import Any
from collections.abc import Iterable

from tests.helpers.fmt import (
    section_header,
    bold,
    dim,
    green,
    red,
    yellow,
)


# ============================================================================
# Internal Helpers
# ============================================================================


def percentile(values: list[float], frac: float, minus_one: bool = False) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    n = len(vals)
    idx = int(frac * n)
    if minus_one:
        idx = max(idx - 1, 0)
    if idx >= n:
        idx = n - 1
    return vals[idx]


def _is_capacity_error(message: str | None) -> bool:
    if not message:
        return False
    msg = message.lower()
    return "server_at_capacity" in msg or "1013" in msg


def _format_error_hint(raw_error: str, all_errors: list[dict[str, Any]]) -> str:
    message = raw_error or "unknown error"
    normalized = message.lower()

    if "authentication_failed" in normalized:
        api_key = os.getenv("TEXT_API_KEY")
        if api_key:
            return "authentication_failed - provided TEXT_API_KEY was rejected"
        return "authentication_failed - TEXT_API_KEY environment variable is missing"

    if "server_at_capacity" in normalized:
        capacity_errors = [err for err in all_errors if _is_capacity_error(err.get("error"))]
        details: list[str] = []
        if capacity_errors:
            details.append(f"rejections={len(capacity_errors)}")
        limit_env = os.getenv("MAX_CONCURRENT_CONNECTIONS")
        if limit_env:
            details.append(f"MAX_CONCURRENT_CONNECTIONS={limit_env}")
        suffix = f" ({', '.join(details)})" if details else ""
        return f"server_at_capacity{suffix}"

    if "connection_closed_ok" in normalized:
        closed_count = sum(1 for err in all_errors if "connection_closed" in str(err.get("error", "")).lower())
        return f"connection closed (code 1000) before completion ({closed_count} affected)"

    if "connection_closed" in normalized:
        return f"connection closed unexpectedly: {message}"

    return message


def _format_latency_line(label: str, samples: list[float]) -> str:
    """Format a latency statistics line."""
    if not samples:
        return ""
    p50 = percentile(samples, 0.5)
    p95 = percentile(samples, 0.95, minus_one=True)
    avg = sum(samples) / len(samples)
    return f"  {label:>12}  avg={avg:>6.0f}ms  p50={p50:>6.0f}ms  p95={p95:>6.0f}ms  {dim(f'(n={len(samples)})')}"


def _print_latency_section(ok_results: Iterable[dict[str, Any]], prefix: str = "") -> None:
    ok_list = list(ok_results)
    tool_ttfb = [r["ttfb_toolcall_ms"] for r in ok_list if r.get("ttfb_toolcall_ms") is not None]
    chat_ttfb = [r["ttfb_chat_ms"] for r in ok_list if r.get("ttfb_chat_ms") is not None]
    first_sentence = [r["first_sentence_ms"] for r in ok_list if r.get("first_sentence_ms") is not None]
    first_3_words = [r["first_3_words_ms"] for r in ok_list if r.get("first_3_words_ms") is not None]

    metrics = [
        ("TTFB (tool)", tool_ttfb),
        ("TTFB (chat)", chat_ttfb),
        ("3-words", first_3_words),
        ("sentence", first_sentence),
    ]
    
    for label, samples in metrics:
        line = _format_latency_line(label, samples)
        if line:
            print(f"{prefix}{line}")


def _print_tagged_section(tag: str, results: list[dict[str, Any]]) -> None:
    ok = [r for r in results if r.get("ok")]
    if not ok:
        return
    print(f"\n  {bold(tag.upper())} transaction:")
    _print_latency_section(ok)


# ============================================================================
# Public API
# ============================================================================


def print_report(
    url: str,
    requests: int,
    concurrency: int,
    results: list[dict[str, Any]],
    *,
    double_ttfb: bool = False,
) -> None:
    """Print benchmark summary report with consistent formatting."""
    ok = [r for r in results if r.get("ok")]
    errs = [r for r in results if not r.get("ok")]
    total_transactions = len(results)

    print(f"\n{section_header('BENCHMARK RESULTS')}")
    
    # Summary line
    ok_str = green(str(len(ok))) if ok else str(len(ok))
    err_str = red(str(len(errs))) if errs else str(len(errs))
    
    if not double_ttfb:
        print(dim(f"  url: {url}"))
        print(dim(f"  requests: {requests}  concurrency: {concurrency}"))
        print(f"  results: {ok_str} ok, {err_str} errors\n")
        _print_latency_section(ok)
    else:
        print(dim(f"  url: {url}"))
        print(dim(f"  connections: {requests}  transactions: {total_transactions}  concurrency: {concurrency}"))
        print(f"  results: {ok_str} ok, {err_str} errors")
        _print_tagged_section("first", [r for r in results if r.get("phase") == 1])
        _print_tagged_section("second", [r for r in results if r.get("phase") == 2])

    if errs:
        print()
        emsg = str(errs[0].get("error", "unknown error"))
        print(f"  {red('ERROR')}: {_format_error_hint(emsg, errs)}")


__all__ = ["print_report", "percentile"]
