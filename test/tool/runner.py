"""Core execution orchestration for the tool regression suite."""

from __future__ import annotations

import os
import sys

_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from common.prompt import select_chat_prompt  # noqa: E402
from config import DEFAULT_WS_PING_INTERVAL, DEFAULT_WS_PING_TIMEOUT  # noqa: E402

from .cases import build_cases
from .executor import run_all_cases
from .reporting import print_failures, print_summary
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
) -> list[CaseResult]:
    """
    Execute the tool-call regression suite and print per-case + summary output.
    """

    cases = build_cases()
    if limit is not None:
        cases = cases[:limit]

    cfg = RunnerConfig(
        ws_url=ws_url,
        gender=gender,
        personality=personality,
        chat_prompt=select_chat_prompt(gender),
        timeout_s=timeout_s,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    )

    results = await run_all_cases(cases, cfg, concurrency=max(1, concurrency))
    print_failures(results)
    print_summary(results)
    return results