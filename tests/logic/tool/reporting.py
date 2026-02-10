"""Reporting and summary helpers for tool regression test output.

This module provides functions for formatting and printing test results,
computing summary statistics, and saving logs to files. It handles both
console output and structured log file generation.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from collections.abc import Iterator, Sequence

from tests.state import CaseResult


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
        return

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


def _case_lines(results: Sequence[CaseResult]) -> list[str]:
    """Return the formatted lines for a list of case results."""
    lines: list[str] = []
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
        lines.extend(_iter_response_lines(result))
    return lines


def _case_block_lines(title: str, results: Sequence[CaseResult]) -> list[str]:
    """Build full block lines (title + case lines)."""
    if not results:
        return []
    return [title, *_case_lines(results)]


def print_case_results(results: Sequence[CaseResult], *, include_successes: bool = False) -> None:
    """Print case results to stdout."""
    subset = results if include_successes else [r for r in results if not r.success]
    title = "=== Results ===" if include_successes else "=== Failures ==="
    for line in _case_block_lines(title, subset):
        print(line)


def _summary_lines(results: Sequence[CaseResult]) -> list[str]:
    """Build the summary lines shared by printers and formatters."""
    total = len(results)
    passed = sum(1 for r in results if r.success)
    failed = total - passed
    accuracy = (passed / total * 100.0) if total else 0.0

    lines = [
        "\n=== Summary ===",
        f"Total test cases: {total}",
        f"Passed: {passed}",
        f"Failed: {failed}",
        f"Accuracy: {accuracy:.1f}%",
    ]

    if failed:
        counter = Counter(r.reason or "unknown" for r in results if not r.success)
        lines.append("Failure breakdown:")
        for reason, count in counter.items():
            lines.append(f"  - {reason}: {count}")

    lines.extend(_latency_summary_lines(results))
    return lines


def print_summary(results: Sequence[CaseResult]) -> None:
    """Print summary statistics to stdout."""
    for line in _summary_lines(results):
        print(line)


def _latency_summary_lines(results: Sequence[CaseResult]) -> list[str]:
    """Format latency statistics from step timings."""
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
        return []

    lines = ["\nLatency (tool response, ms):"]
    lines.append(_format_latency_line("TTFB", ttfb_samples))
    lines.append(_format_latency_line("Total", total_samples))
    return lines


def _format_latency_line(label: str, samples: list[float]) -> str:
    """Format a single latency statistics line."""
    if not samples:
        return f"  {label}: no samples"
    values = sorted(samples)
    p50 = _percentile(values, 50)
    p90 = _percentile(values, 90)
    p95 = _percentile(values, 95)
    return f"  {label}: p50={p50:.1f} ms  p90={p90:.1f} ms  p95={p95:.1f} ms  (n={len(values)})"


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


def format_case_results(results: Sequence[CaseResult], *, include_successes: bool = False) -> str:
    """Format case results as a string instead of printing."""
    subset = results if include_successes else [r for r in results if not r.success]
    title = "=== Results ===" if include_successes else "=== Failures ==="
    lines = _case_block_lines(title, subset)
    return "\n".join(lines) if lines else ""


def format_summary(results: Sequence[CaseResult]) -> str:
    """Format summary as a string instead of printing."""
    return "\n".join(_summary_lines(results))


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
    from pathlib import Path  # noqa: PLC0415
    from datetime import datetime  # noqa: PLC0415

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
