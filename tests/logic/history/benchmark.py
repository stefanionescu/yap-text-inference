"""Benchmark runner for history recall tests with warm history.

This module orchestrates concurrent benchmark runs where each connection
starts with pre-built warm history and cycles through recall messages.
Reuses the standard benchmark's reporting and worker distribution logic.
"""

from __future__ import annotations

import asyncio
from typing import Any

from tests.helpers.prompt import select_chat_prompt
from tests.logic.benchmark.reporting import print_report
from tests.messages.history import HISTORY_RECALL_MESSAGES
from tests.helpers.concurrency import distribute_requests, sanitize_concurrency

from .types import HistoryBenchConfig
from .connection import execute_history_connection


def _build_config(
    url: str,
    api_key: str | None,
    gender: str,
    personality: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
) -> HistoryBenchConfig:
    """Build history benchmark configuration."""
    chat_prompt = select_chat_prompt(gender)
    return HistoryBenchConfig(
        url=url,
        api_key=api_key,
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
        timeout_s=timeout_s,
        sampling=sampling,
    )


async def _run_worker(count: int, cfg: HistoryBenchConfig) -> list[dict[str, Any]]:
    """Execute multiple sequential connections for a single worker."""
    results: list[dict[str, Any]] = []
    for _ in range(count):
        results.extend(await execute_history_connection(cfg))
    return results


async def _run_concurrent_benchmark(
    total_connections: int,
    concurrency: int,
    cfg: HistoryBenchConfig,
) -> list[dict[str, Any]]:
    """Run benchmark with concurrent connections.

    Each connection cycles through all HISTORY_RECALL_MESSAGES, so
    total transactions = total_connections * len(HISTORY_RECALL_MESSAGES).
    """
    counts = distribute_requests(total_connections, concurrency)
    tasks = [
        asyncio.create_task(_run_worker(count, cfg))
        for count in counts
        if count > 0
    ]
    nested = await asyncio.gather(*tasks)
    return [item for sublist in nested for item in sublist]


async def run_history_benchmark(
    url: str,
    api_key: str | None,
    gender: str,
    personality: str,
    requests: int,
    concurrency: int,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
) -> bool:
    """Run history benchmark with warm history and recall messages.

    Args:
        url: WebSocket URL.
        api_key: API key for authentication.
        gender: Gender for persona selection.
        personality: Personality name.
        requests: Number of connections to run.
        concurrency: Max concurrent connections.
        timeout_s: Per-transaction timeout in seconds.
        sampling: Optional sampling parameters.

    Returns:
        True if all transactions succeeded, False if any failed.
    """
    cfg = _build_config(url, api_key, gender, personality, timeout_s, sampling)
    requests, concurrency = sanitize_concurrency(requests, concurrency)

    results = await _run_concurrent_benchmark(requests, concurrency, cfg)

    # Calculate actual transaction count for reporting
    messages_per_conn = len(HISTORY_RECALL_MESSAGES)
    expected_transactions = requests * messages_per_conn

    print_report(
        url=cfg.url,
        requests=expected_transactions,
        concurrency=concurrency,
        results=results,
    )
    return all(r.get("ok") for r in results)


__all__ = ["run_history_benchmark"]

