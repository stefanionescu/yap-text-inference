#!/usr/bin/env python3
"""
Concurrent benchmark for the WebSocket /ws endpoint.

Runs N total sessions with up to M concurrent connections. For each request,
records:
- ttfb_toolcall_ms: time to receive toolcall decision
- ttfb_chat_ms: time to first chat token (if chat happens)
- first_sentence_ms: time to first complete sentence (if chat happens)
- first_3_words_ms: time to first three words (if chat happens)

Prints p50/p95 for each metric across completed requests. No intermediate logs.

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- TEXT_API_KEY: API key for authentication (required, no default)
- GENDER: female|male (default: female)
- PERSONALITY: personality (default: flirty)

Note: API key authentication is required. The client will automatically
append the API key as a query parameter to all WebSocket connections.

If concurrency exceeds the server's MAX_CONCURRENT_CONNECTIONS limit, the
benchmark will surface the resulting "server_at_capacity" errors so you can
see how many sessions were rejected by the guardrail.
"""

from __future__ import annotations

import os
import sys
import asyncio
import argparse
from importlib import import_module
from collections.abc import Callable


def _load_setup_repo_path() -> Callable[[], str]:
    try:
        return import_module("tests.helpers.setup").setup_repo_path
    except ModuleNotFoundError:
        return import_module("helpers.setup").setup_repo_path


setup_repo_path = _load_setup_repo_path()

setup_repo_path()

from tests.helpers.cli import add_sampling_args, add_connection_args, build_sampling_payload  # noqa: E402
from tests.config import (  # noqa: E402
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_SERVER_WS_URL,
    BENCHMARK_DEFAULT_REQUESTS,
    BENCHMARK_BURST_MODE_DEFAULT,
    BENCHMARK_BURST_SIZE_DEFAULT,
    BENCHMARK_DEFAULT_CONCURRENCY,
    BENCHMARK_DEFAULT_TIMEOUT_SEC,
    BENCHMARK_WINDOW_DURATION_DEFAULT,
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Yap Text Inference WS server")
    add_connection_args(
        p,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(p)
    p.add_argument("message", nargs="*", help="optional user message for all requests")
    p.add_argument(
        "--requests",
        "-n",
        type=int,
        default=BENCHMARK_DEFAULT_REQUESTS,
        help="total number of requests",
    )
    p.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=BENCHMARK_DEFAULT_CONCURRENCY,
        help="max in-flight requests",
    )
    p.add_argument(
        "--timeout",
        type=float,
        default=BENCHMARK_DEFAULT_TIMEOUT_SEC,
        help="per-request total timeout (s)",
    )
    p.add_argument(
        "--gender",
        dest="gender",
        choices=["female", "male"],
        default=os.getenv("GENDER", DEFAULT_GENDER),
        help="gender",
    )
    p.add_argument(
        "--personality",
        dest="personality",
        default=os.getenv("PERSONALITY", DEFAULT_PERSONALITY),
        help="personality (e.g., wholesome, savage, flirty)",
    )
    p.add_argument(
        "--double-ttfb",
        action="store_true",
        help="send two sequential start messages per connection and report metrics separately",
    )
    p.add_argument(
        "--burst-mode",
        choices=["instant", "windowed"],
        default=BENCHMARK_BURST_MODE_DEFAULT,
        help=("transaction distribution mode: 'instant' sends all at once (default), 'windowed' sends in timed bursts"),
    )
    p.add_argument(
        "--burst-size",
        type=int,
        default=BENCHMARK_BURST_SIZE_DEFAULT,
        help="number of transactions to send per window (only used with --burst-mode=windowed)",
    )
    p.add_argument(
        "--window-duration",
        type=float,
        default=BENCHMARK_WINDOW_DURATION_DEFAULT,
        help="duration of each burst window in seconds (only used with --burst-mode=windowed)",
    )
    args = p.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    """Thin orchestrator: parse CLI args and run the benchmark."""
    from tests.logic.benchmark.runner import run_benchmark  # noqa: PLC0415

    args = _parse_args()
    success = asyncio.run(run_benchmark(args))
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
