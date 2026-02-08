"""Benchmark runner for WebSocket /ws endpoint performance testing.

This module orchestrates concurrent benchmark runs against the inference server.
It supports both instant mode (all requests at once) and windowed burst mode
(batched requests with configurable delays). Metrics collected include tool
TTFB, chat TTFB, time to first sentence, and time to first 3 words.
"""

from __future__ import annotations

from tests.state import BenchmarkConfig
from tests.helpers.selection import choose_message
from tests.config import BENCHMARK_FALLBACK_MESSAGE
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.concurrency import sanitize_concurrency

from .reporting import print_report
from .workers import run_instant_benchmark, run_windowed_benchmark


def _build_config(args) -> BenchmarkConfig:
    """Build benchmark configuration from CLI arguments."""
    message = choose_message(args.message, fallback=BENCHMARK_FALLBACK_MESSAGE)
    sampling = getattr(args, "sampling", None) or None
    double_ttfb = bool(getattr(args, "double_ttfb", False))

    # chat_prompt is required - always select one based on gender
    chat_prompt = select_chat_prompt(args.gender)

    return BenchmarkConfig(
        url=args.server,
        api_key=args.api_key,
        gender=args.gender,
        style=args.personality,
        chat_prompt=chat_prompt,
        message=message,
        timeout_s=float(args.timeout),
        sampling=sampling,
        double_ttfb=double_ttfb,
    )


async def run_benchmark(args) -> bool:
    """Main benchmark entry point - parse args and execute the benchmark.

    Returns:
        True if all requests succeeded, False if any failed.
    """
    cfg = _build_config(args)
    requests, concurrency = sanitize_concurrency(
        int(args.requests),
        int(args.concurrency),
    )

    burst_mode = getattr(args, "burst_mode", "instant")
    burst_size = max(1, int(getattr(args, "burst_size", 3)))
    window_duration = float(getattr(args, "window_duration", 0.5))

    if burst_mode == "windowed":
        results = await run_windowed_benchmark(
            requests,
            burst_size,
            window_duration,
            cfg,
        )
    else:
        results = await run_instant_benchmark(requests, concurrency, cfg)

    print_report(
        cfg.url,
        requests,
        concurrency,
        results,
        double_ttfb=cfg.double_ttfb,
    )
    return all(r.get("ok") for r in results)


__all__ = ["run_benchmark"]
