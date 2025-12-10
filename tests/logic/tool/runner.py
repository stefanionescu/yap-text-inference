"""Core execution orchestration for the tool regression suite."""

from __future__ import annotations

import os
import sys

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.helpers.prompt import (  # noqa: E402
    PROMPT_MODE_BOTH,
    select_chat_prompt,
    should_send_chat_prompt,
)
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
    timeout_s: float,
    concurrency: int,
    limit: int | None = None,
    show_successes: bool = False,
    prompt_mode: str | None = None,
    max_steps_per_case: int | None = None,
) -> list[CaseResult]:
    """
    Execute the tool-call regression suite and print per-case + summary output.
    """

    cases = build_cases()
    if limit is not None:
        cases = cases[:limit]
    cases = list(cases)

    step_cap = max_steps_per_case if max_steps_per_case is not None else None
    if step_cap is not None and step_cap <= 0:
        step_cap = None

    skipped_labels: list[str] = []
    if step_cap is not None:
        allowed_cases: list[ToolTestCase] = []
        for case in cases:
            if len(case.steps) <= step_cap:
                allowed_cases.append(case)
            else:
                skipped_labels.append(case.label or case.name)
        if skipped_labels:
            shown = ", ".join(skipped_labels[:5])
            suffix = " ..." if len(skipped_labels) > 5 else ""
            print(
                f"Skipping {len(skipped_labels)} tool cases exceeding {step_cap} steps: "
                f"{shown}{suffix}"
            )
        cases = allowed_cases

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

    normalized_mode = prompt_mode or PROMPT_MODE_BOTH
    chat_prompt = select_chat_prompt(gender) if should_send_chat_prompt(normalized_mode) else None
    if chat_prompt is None:
        print("Tool-only suite running without chat prompts.")

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
    return results