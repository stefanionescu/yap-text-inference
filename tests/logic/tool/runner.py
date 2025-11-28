"""Core execution orchestration for the tool regression suite."""

from __future__ import annotations

import os
import sys

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.helpers.prompt import select_chat_prompt  # noqa: E402
from tests.config import DEFAULT_WS_PING_INTERVAL, DEFAULT_WS_PING_TIMEOUT  # noqa: E402

from .cases import build_cases
from .executor import run_all_cases
from .reporting import print_case_results, print_summary
from .types import CaseResult, RunnerConfig

__all__ = ["run_suite"]


async def run_suite(
    *,
    ws_url: str,
    gender: str,
    personality: str,
    tool_prompt: str,
    timeout_s: float,
    concurrency: int,
    limit: int | None = None,
    show_successes: bool = False,
) -> list[CaseResult]:
    """
    Execute the tool-call regression suite and print per-case + summary output.
    """

    cases = build_cases()
    if limit is not None:
        cases = cases[:limit]
    cases = list(cases)
    total_cases = len(cases)
    effective_concurrency = max(1, concurrency)

    progress_cb = None
    if total_cases:
        bar_width = 30
        print(f"Running {total_cases} tool cases (concurrency={effective_concurrency})...")

        def _render_progress(completed: int, total: int) -> None:
            total = max(1, total)
            ratio = min(max(completed / total, 0.0), 1.0)
            filled = int(bar_width * ratio)
            bar = "#" * filled + "-" * (bar_width - filled)
            line = f"\rProgress [{bar}] {completed}/{total} ({ratio * 100:5.1f}%)"
            end = "\n" if completed >= total else ""
            print(line, end=end, flush=True)

        progress_cb = _render_progress
    else:
        print("No tool cases to run.")

    cfg = RunnerConfig(
        ws_url=ws_url,
        gender=gender,
        personality=personality,
        chat_prompt=select_chat_prompt(gender),
        tool_prompt=tool_prompt,
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
    return results