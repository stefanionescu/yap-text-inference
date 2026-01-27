#!/usr/bin/env python3
"""History recall test for warm history and prefix caching.

Connects to the WebSocket server with a pre-built conversation history, then
sends follow-up messages to test the assistant's recall of earlier exchanges.
Tracks TTFB for each response and prints summary statistics (p50, p90, p95).

Benchmark mode (--bench): Runs concurrent connections with warm history,
suppresses per-message output, and prints aggregate statistics at the end.

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- TEXT_API_KEY: API key for authentication (required, no default)
- GENDER: female|male (default: female)
- PERSONALITY: personality (default: flirty)

Usage:
  python3 tests/history.py
  python3 tests/history.py --gender male
  python3 tests/history.py --temperature 0.8 --top-p 0.9
  python3 tests/history.py --bench -n 16 -c 8
"""

from __future__ import annotations

import os
import sys
import asyncio
import argparse

try:
    from tests.helpers.setup import setup_repo_path
except ModuleNotFoundError:
    from helpers.setup import setup_repo_path  # type: ignore[import-not-found]

setup_repo_path()

from tests.helpers.errors import ServerError
from tests.helpers.cli import add_sampling_args, add_connection_args, build_sampling_payload
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_SERVER_WS_URL,
    HISTORY_BENCH_DEFAULT_REQUESTS,
    HISTORY_BENCH_DEFAULT_CONCURRENCY,
    HISTORY_BENCH_DEFAULT_TIMEOUT_SEC,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="History recall test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    parser.add_argument(
        "--gender",
        dest="gender",
        choices=["female", "male"],
        default=os.getenv("GENDER", DEFAULT_GENDER),
        help="gender",
    )
    parser.add_argument(
        "--personality",
        dest="personality",
        default=os.getenv("PERSONALITY", DEFAULT_PERSONALITY),
        help="personality (e.g., wholesome, savage, flirty)",
    )
    parser.add_argument(
        "--bench",
        action="store_true",
        help="run in benchmark mode with concurrent connections",
    )
    parser.add_argument(
        "--requests",
        "-n",
        type=int,
        default=HISTORY_BENCH_DEFAULT_REQUESTS,
        help="number of connections for benchmark mode",
    )
    parser.add_argument(
        "--concurrency",
        "-c",
        type=int,
        default=HISTORY_BENCH_DEFAULT_CONCURRENCY,
        help="max concurrent connections for benchmark mode",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=HISTORY_BENCH_DEFAULT_TIMEOUT_SEC,
        help="per-transaction timeout in seconds (benchmark mode)",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def _run_interactive(args: argparse.Namespace) -> None:
    """Run the interactive history recall test."""
    from tests.logic.history.runner import run_test

    try:
        asyncio.run(
            run_test(
                args.server,
                args.api_key,
                args.gender,
                args.personality,
                args.sampling or None,
            )
        )
    except ServerError:
        sys.exit(1)
    except KeyboardInterrupt:
        pass


def _run_benchmark(args: argparse.Namespace) -> None:
    """Run the benchmark mode with concurrent connections."""
    from tests.logic.history.benchmark import run_history_benchmark

    success = asyncio.run(
        run_history_benchmark(
            url=args.server,
            api_key=args.api_key,
            gender=args.gender,
            personality=args.personality,
            requests=args.requests,
            concurrency=args.concurrency,
            timeout_s=args.timeout,
            sampling=args.sampling or None,
        )
    )
    if not success:
        sys.exit(1)


def main() -> None:
    """Thin orchestrator: parse CLI args and run the appropriate test mode."""
    args = _parse_args()

    if args.bench:
        _run_benchmark(args)
    else:
        _run_interactive(args)


if __name__ == "__main__":
    main()
