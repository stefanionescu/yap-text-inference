"""Formatting and summary helpers for tool regression output."""

from __future__ import annotations

import json
import math
from collections import Counter
from typing import Iterator, Sequence

from .types import CaseResult

__all__ = ["print_case_results", "print_summary"]


def _format_case_summary(result: CaseResult) -> str:
    status = "PASS" if result.success else "FAIL"
    reason = ""
    # Only include the failure reason to keep successful output concise.
    if not result.success and result.reason:
        reason = f" ({result.reason})"
    return f"[{status}] {result.case.name}{reason} — {result.case.label}"


def _iter_response_lines(result: CaseResult) -> Iterator[str]:
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
    if include_successes:
        _print_case_block("=== Results ===", results)
        return

    failures = [r for r in results if not r.success]
    _print_case_block("=== Failures ===", failures)


def print_summary(results: Sequence[CaseResult]) -> None:
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

