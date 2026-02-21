"""Worker distribution and task management for benchmark runs.

This module provides utilities for distributing benchmark requests across
concurrent workers and managing the async task lifecycle.
"""

from __future__ import annotations

import time
import asyncio
from typing import Any
from tests.state import BenchmarkConfig
from .connection import execute_connection
from tests.helpers.concurrency import distribute_requests


async def run_worker(count: int, cfg: BenchmarkConfig) -> list[dict[str, Any]]:
    """Execute multiple sequential connections for a single worker.

    Args:
        count: Number of connections this worker should make.
        cfg: Benchmark configuration.

    Returns:
        Flattened list of results from all connections.
    """
    results: list[dict[str, Any]] = []
    for _ in range(count):
        results.extend(await execute_connection(cfg))
    return results


async def run_instant_benchmark(
    total_requests: int,
    concurrency: int,
    cfg: BenchmarkConfig,
) -> list[dict[str, Any]]:
    """Run benchmark in instant mode - all workers start simultaneously.

    Distributes requests across workers and launches them all at once.

    Args:
        total_requests: Total number of benchmark requests.
        concurrency: Number of concurrent workers.
        cfg: Benchmark configuration.

    Returns:
        Flattened list of all results.
    """
    counts = distribute_requests(total_requests, concurrency)
    tasks = [asyncio.create_task(run_worker(count, cfg)) for count in counts if count > 0]
    nested = await asyncio.gather(*tasks)
    return [item for sublist in nested for item in sublist]


async def run_windowed_benchmark(
    total_requests: int,
    burst_size: int,
    window_duration: float,
    cfg: BenchmarkConfig,
) -> list[dict[str, Any]]:
    """Run benchmark in windowed burst mode.

    Sends `burst_size` concurrent requests, waits for `window_duration`,
    then repeats until all requests are sent.

    Args:
        total_requests: Total number of benchmark requests.
        burst_size: Number of concurrent requests per window.
        window_duration: Duration of each window in seconds.
        cfg: Benchmark configuration.

    Returns:
        Flattened list of all results.
    """
    results: list[dict[str, Any]] = []
    remaining = total_requests

    while remaining > 0:
        batch = min(burst_size, remaining)
        window_start = time.perf_counter()

        tasks = [asyncio.create_task(execute_connection(cfg)) for _ in range(batch)]
        nested = await asyncio.gather(*tasks)
        for sublist in nested:
            results.extend(sublist)

        remaining -= batch

        if remaining > 0:
            elapsed = time.perf_counter() - window_start
            sleep_time = window_duration - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    return results


__all__ = [
    "run_worker",
    "run_instant_benchmark",
    "run_windowed_benchmark",
]
