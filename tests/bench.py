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

import argparse
import asyncio
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tests.helpers.cli import add_connection_args, add_sampling_args, build_sampling_payload
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_SERVER_WS_URL,
    BENCHMARK_DEFAULT_CONCURRENCY,
    BENCHMARK_DEFAULT_REQUESTS,
    BENCHMARK_DEFAULT_TIMEOUT_SEC,
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
        choices=["female", "male", "woman", "man"],
        default=os.getenv("GENDER", DEFAULT_GENDER),
        help="gender (normalized by server)",
    )
    p.add_argument(
        "--personality",
        dest="personality",
        default=os.getenv("PERSONALITY", DEFAULT_PERSONALITY),
        help="personality (e.g., wholesome, savage, flirty)",
    )
    args = p.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    """Thin orchestrator: parse CLI args and run the benchmark."""
    from tests.logic.benchmark.runner import run_benchmark

    args = _parse_args()
    asyncio.run(run_benchmark(args))


if __name__ == "__main__":
    main()


