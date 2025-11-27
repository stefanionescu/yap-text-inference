"""Formatting and summary helpers for tool regression output."""

from __future__ import annotations

import json
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
        if not result.success and result.detail:
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

