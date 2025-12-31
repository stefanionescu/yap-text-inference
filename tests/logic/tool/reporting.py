"""Reporting and summary helpers for tool regression test output.

This module provides functions for formatting and printing test results,
computing summary statistics, and saving logs to files. It handles both
console output and structured log file generation.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Iterator, Sequence

from .types import CaseResult


def _format_case_summary(result: CaseResult) -> str:
    """Format a single case result as a one-line summary."""
    status = "PASS" if result.success else "FAIL"
    reason = ""
    # Only include the failure reason to keep successful output concise.
    if not result.success and result.reason:
        reason = f" ({result.reason})"
    return f"[{status}] {result.case.name}{reason} — {result.case.label}"


def _iter_response_lines(result: CaseResult) -> Iterator[str]:
    """Iterate over formatted response lines for a case result."""
    responses = result.responses or []
    if not responses:
        return iter(())

    def _stringify(value: object) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except TypeError:
            return repr(value)

    multi = len(responses) > 1
    for idx, raw in enumerate(responses, start=1):
        label = "response" if not multi else f"response[{idx}]"
        yield f"        {label}: {_stringify(raw)}"


def _print_case_block(title: str, results: Sequence[CaseResult]) -> None:
    """Print a block of case results with a title."""
    if not results:
        return

    print(title)
    for result in results:
        print(_format_case_summary(result))
        failures = result.failures or []
        if failures:
            for idx, failure in enumerate(failures, start=1):
                label = "failure" if len(failures) == 1 else f"failure[{idx}]"
                detail = failure.detail or failure.reason
                print(f"        {label}: {detail}")
        elif not result.success and result.detail:
            print(f"        {result.detail}")
        for line in _iter_response_lines(result):
            print(line)


def print_case_results(results: Sequence[CaseResult], *, include_successes: bool = False) -> None:
    """Print case results to stdout."""
    if include_successes:
        _print_case_block("=== Results ===", results)
        return

    failures = [r for r in results if not r.success]
    _print_case_block("=== Failures ===", failures)


def print_summary(results: Sequence[CaseResult]) -> None:
    """Print summary statistics to stdout."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    accuracy = (passed / total * 100.0) if total else 0.0
    print("\n=== Summary ===")
    print(f"Total test cases: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Accuracy: {accuracy:.1f}%")

    if failed:
        counter = Counter(r.reason or "unknown" for r in results if not r.success)
        print("Failure breakdown:")
        for reason, count in counter.items():
            print(f"  - {reason}: {count}")

    _print_latency_summary(results)


def _print_latency_summary(results: Sequence[CaseResult]) -> None:
    """Print latency statistics from step timings."""
    ttfb_samples: list[float] = []
    total_samples: list[float] = []
    for result in results:
        if not result.step_timings:
            continue
        for timing in result.step_timings:
            if timing.ttfb_ms is not None:
                ttfb_samples.append(timing.ttfb_ms)
            if timing.total_ms is not None:
                total_samples.append(timing.total_ms)

    if not ttfb_samples and not total_samples:
        return

    print("\nLatency (tool response, ms):")
    _print_latency_line("TTFB", ttfb_samples)
    _print_latency_line("Total", total_samples)


def _print_latency_line(label: str, samples: list[float]) -> None:
    """Print a single latency statistics line."""
    if not samples:
        print(f"  {label}: no samples")
        return
    values = sorted(samples)
    p50 = _percentile(values, 50)
    p90 = _percentile(values, 90)
    p95 = _percentile(values, 95)
    print(
        f"  {label}: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})"
    )


def _percentile(sorted_values: list[float], percentile: float) -> float:
    """Compute the given percentile from sorted values."""
    if not sorted_values:
        raise ValueError("percentile requires at least one value")
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (percentile / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[f] * (c - k)
    d1 = sorted_values[c] * (k - f)
    return d0 + d1


def _format_case_block_string(title: str, results: Sequence[CaseResult]) -> str:
    """Format a case block as a string instead of printing."""
    if not results:
        return ""
    
    lines = [title]
    for result in results:
        lines.append(_format_case_summary(result))
        failures = result.failures or []
        if failures:
            for idx, failure in enumerate(failures, start=1):
                label = "failure" if len(failures) == 1 else f"failure[{idx}]"
                detail = failure.detail or failure.reason
                lines.append(f"        {label}: {detail}")
        elif not result.success and result.detail:
            lines.append(f"        {result.detail}")
        for line in _iter_response_lines(result):
            lines.append(line)
    return "\n".join(lines)


def format_case_results(results: Sequence[CaseResult], *, include_successes: bool = False) -> str:
    """Format case results as a string instead of printing."""
    if include_successes:
        return _format_case_block_string("=== Results ===", results)
    
    failures = [r for r in results if not r.success]
    return _format_case_block_string("=== Failures ===", failures)


def format_summary(results: Sequence[CaseResult]) -> str:
    """Format summary as a string instead of printing."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    accuracy = (passed / total * 100.0) if total else 0.0
    
    lines = ["\n=== Summary ==="]
    lines.append(f"Total test cases: {total}")
    lines.append(f"Passed: {passed}")
    lines.append(f"Failed: {failed}")
    lines.append(f"Accuracy: {accuracy:.1f}%")
    
    if failed:
        counter = Counter(r.reason or "unknown" for r in results if not r.success)
        lines.append("Failure breakdown:")
        for reason, count in counter.items():
            lines.append(f"  - {reason}: {count}")
    
    # Add latency summary
    ttfb_samples: list[float] = []
    total_samples: list[float] = []
    for result in results:
        if not result.step_timings:
            continue
        for timing in result.step_timings:
            if timing.ttfb_ms is not None:
                ttfb_samples.append(timing.ttfb_ms)
            if timing.total_ms is not None:
                total_samples.append(timing.total_ms)
    
    if ttfb_samples or total_samples:
        lines.append("\nLatency (tool response, ms):")
        if ttfb_samples:
            values = sorted(ttfb_samples)
            p50 = _percentile(values, 50)
            p90 = _percentile(values, 90)
            p95 = _percentile(values, 95)
            lines.append(
                f"  TTFB: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})"
            )
        else:
            lines.append("  TTFB: no samples")
        
        if total_samples:
            values = sorted(total_samples)
            p50 = _percentile(values, 50)
            p90 = _percentile(values, 90)
            p95 = _percentile(values, 95)
            lines.append(
                f"  Total: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})"
            )
        else:
            lines.append("  Total: no samples")
    
    return "\n".join(lines)


def save_logs(
    results: Sequence[CaseResult],
    *,
    skipped_count: int = 0,
    skipped_step_cap: int | None = None,
    total_cases: int = 0,
    concurrency: int = 1,
    include_successes: bool = False,
) -> str:
    """
    Save test logs to a file with a unique name in tests/results/.
    Returns the path to the saved log file.
    """
    import os
    from datetime import datetime
    from pathlib import Path
    
    # Create results directory if it doesn't exist
    test_dir = Path(__file__).resolve().parent.parent.parent
    results_dir = test_dir / "results"
    results_dir.mkdir(exist_ok=True)
    
    # Generate unique filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = results_dir / f"tool_test_{timestamp}.log"
    
    # Build log content
    log_lines = []
    
    # Header
    log_lines.append("=" * 80)
    log_lines.append(f"Tool Test Run - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log_lines.append("=" * 80)
    log_lines.append("")
    
    # Skipped tests info
    if skipped_count > 0 and skipped_step_cap is not None:
        log_lines.append(f"Skipping {skipped_count} tool cases exceeding {skipped_step_cap} steps")
        log_lines.append("")
    
    # Test execution info
    if total_cases > 0:
        log_lines.append(f"Running {total_cases} tool cases (concurrency={concurrency})...")
        log_lines.append("")
    
    # Case results
    case_results_str = format_case_results(results, include_successes=include_successes)
    if case_results_str:
        log_lines.append(case_results_str)
        log_lines.append("")
    
    # Summary
    summary_str = format_summary(results)
    log_lines.append(summary_str)
    
    # Write to file
    log_content = "\n".join(log_lines)
    log_file.write_text(log_content, encoding="utf-8")
    
    return str(log_file)


__all__ = ["print_case_results", "print_summary", "format_case_results", "format_summary", "save_logs"]
