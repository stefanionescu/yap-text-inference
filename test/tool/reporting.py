"""Formatting and summary helpers for tool regression output."""

from __future__ import annotations

from collections import Counter
from typing import Sequence

from .types import CaseResult

__all__ = ["print_case_result", "print_summary"]


def print_case_result(result: CaseResult) -> None:
    status = "PASS" if result.success else "FAIL"
    reason = f" ({result.reason})" if result.reason else ""
    summary = f"[{status}] {result.case.name}{reason} — {result.case.label}"
    print(summary)
    if not result.success and result.detail:
        print(f"        {result.detail}")


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
        print("Sample failures:")
        for result in (r for r in results if not r.success)[:5]:
            snippet = result.detail or "no detail"
            print(f"    * {result.case.name}: {snippet}")

