"""Core execution orchestration for the tool regression suite.

This module provides the run_suite function that orchestrates the entire
tool test run: loading cases, filtering by step count, executing with
concurrency, and reporting results.
"""

from __future__ import annotations

from tests.helpers.prompt import select_chat_prompt
from tests.config import PROGRESS_BAR_WIDTH, DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL

from .cases import build_cases
from .executor import run_all_cases
from tests.state import CaseResult, RunnerConfig, ToolTestCase
from .reporting import save_logs, print_summary, print_case_results

# ============================================================================
# Internal Helpers
# ============================================================================


def _filter_by_step_count(
    cases: list[ToolTestCase],
    step_cap: int | None,
) -> tuple[list[ToolTestCase], int]:
    """Filter cases by step count, returning filtered list and skip count."""
    if step_cap is None:
        return cases, 0
    
    allowed: list[ToolTestCase] = []
    skipped_labels: list[str] = []
    
    for case in cases:
        if len(case.steps) <= step_cap:
            allowed.append(case)
        else:
            skipped_labels.append(case.label or case.name)
    
    skipped_count = len(skipped_labels)
    if skipped_count > 0:
        print(f"Skipping {skipped_count} tool cases exceeding {step_cap} steps")
    
    return allowed, skipped_count


def _make_progress_renderer() -> callable:
    """Create a progress callback for the progress bar."""
    def render(completed: int, total: int) -> None:
        total = max(1, total)
        ratio = min(max(completed / total, 0.0), 1.0)
        filled = int(PROGRESS_BAR_WIDTH * ratio)
        bar = "#" * filled + "-" * (PROGRESS_BAR_WIDTH - filled)
        line = f"\rProgress [{bar}] {completed}/{total} ({ratio * 100:5.1f}%)"
        end = "\n" if completed >= total else ""
        print(line, end=end, flush=True)
    return render


# ============================================================================
# Public API
# ============================================================================


async def run_suite(
    *,
    ws_url: str,
    gender: str,
    personality: str,
    timeout_s: float,
    concurrency: int,
    limit: int | None = None,
    show_successes: bool = False,
    max_steps_per_case: int | None = None,
) -> list[CaseResult]:
    """
    Execute the tool-call regression suite and print per-case + summary output.

    Args:
        ws_url: WebSocket URL with API key included.
        gender: Assistant gender for persona selection.
        personality: Assistant personality.
        timeout_s: Per-turn timeout in seconds.
        concurrency: Maximum concurrent test cases.
        limit: Optional limit on number of cases to run.
        show_successes: Include passing cases in output.
        max_steps_per_case: Skip cases with more steps than this.

    Returns:
        List of CaseResult objects for all executed cases.
    """
    # Load and limit cases
    cases = build_cases()
    if limit is not None:
        cases = cases[:limit]
    cases = list(cases)

    # Normalize step cap
    step_cap = max_steps_per_case
    if step_cap is not None and step_cap <= 0:
        step_cap = None

    # Filter by step count
    cases, skipped_count = _filter_by_step_count(cases, step_cap)

    total_cases = len(cases)
    effective_concurrency = max(1, concurrency)

    # Setup progress display
    if total_cases:
        print(f"Running {total_cases} tool cases (concurrency={effective_concurrency})...")
        progress_cb = _make_progress_renderer()
    else:
        print("No tool cases to run.")
        progress_cb = None

    # chat_prompt is required - always select one based on gender
    chat_prompt = select_chat_prompt(gender)

    cfg = RunnerConfig(
        ws_url=ws_url,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        timeout_s=timeout_s,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    )

    results = await run_all_cases(
        cases,
        cfg,
        concurrency=effective_concurrency,
        progress_cb=progress_cb,
    )
    print_case_results(results, include_successes=show_successes)
    print_summary(results)
    
    # Save logs to file
    log_file = save_logs(
        results,
        skipped_count=skipped_count,
        skipped_step_cap=step_cap,
        total_cases=total_cases,
        concurrency=effective_concurrency,
        include_successes=show_successes,
    )
    print(f"\nLogs saved to: {log_file}")
    
    return results


__all__ = ["run_suite"]
