"""Result printing functions for cancel test output.

This module provides functions that format and print test results
to the console using the standard test output formatting helpers.
"""

from __future__ import annotations

from tests.state import CancelClientResult, NormalClientResult
from tests.helpers.fmt import (
    red,
    green,
    format_user,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_metrics_inline,
)

CANCEL_TEST_MESSAGE = "hey there! tell me a story about a magical forest"
RECOVERY_PREVIEW_CHARS = 80


def print_cancel_client_result(result: CancelClientResult) -> tuple[int, int]:
    """Print results for the canceling client.

    Args:
        result: Combined result from the canceling client.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    passed_count = 0
    failed_count = 0

    # Cancel phase
    if result.cancel_phase.passed:
        print(f"  {green('✓')} [cancel] {green('PASS')}")
        passed_count += 1
    else:
        reason = result.cancel_phase.error or "cancelled=False"
        print(f"  {red('✗')} [cancel] {red('FAIL')}: {reason}")
        failed_count += 1

    # Drain phase
    if result.drain_phase.passed:
        print(f"  {green('✓')} [drain] {green('PASS')}")
        passed_count += 1
    else:
        reason = result.drain_phase.error or "spurious messages received"
        print(f"  {red('✗')} [drain] {red('FAIL')}: {reason}")
        failed_count += 1

    # Recovery phase
    if result.recovery_phase.passed:
        print(exchange_header())
        print(f"  {format_user(CANCEL_TEST_MESSAGE)}")
        response_preview = result.recovery_phase.response_text[:RECOVERY_PREVIEW_CHARS]
        if len(result.recovery_phase.response_text) > RECOVERY_PREVIEW_CHARS:
            response_preview += "..."
        print(f"  {format_assistant(response_preview)}")
        print(f"  {format_metrics_inline(result.recovery_phase.metrics)}")
        print(exchange_footer())
        print(f"  {green('✓')} [recovery] {green('PASS')}")
        passed_count += 1
    else:
        reason = result.recovery_phase.error or "empty response"
        print(f"  {red('✗')} [recovery] {red('FAIL')}: {reason}")
        failed_count += 1

    return passed_count, failed_count


def print_normal_client_results(results: list[NormalClientResult]) -> tuple[int, int]:
    """Print results for normal clients.

    Args:
        results: List of results from normal clients.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    passed_count = 0
    failed_count = 0

    for result in results:
        label = f"client-{result.client_id}"
        if result.passed:
            print(f"  {green('✓')} [{label}] {green('PASS')}")
            passed_count += 1
        else:
            reason = result.error or "empty response"
            print(f"  {red('✗')} [{label}] {red('FAIL')}: {reason}")
            failed_count += 1

    return passed_count, failed_count


__all__ = [
    "CANCEL_TEST_MESSAGE",
    "print_cancel_client_result",
    "print_normal_client_results",
]
