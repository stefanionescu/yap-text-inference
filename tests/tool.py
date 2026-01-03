#!/usr/bin/env python3
"""
Tool model regression tester CLI.

Parses command-line arguments and defers execution to tool.runner.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

try:
    from tests.helpers.setup import setup_repo_path
except ModuleNotFoundError:
    from helpers.setup import setup_repo_path  # type: ignore[import-not-found]

setup_repo_path()

from tests.helpers.cli import add_connection_args
from tests.helpers.websocket import with_api_key
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    TOOL_WS_MAX_MESSAGES_PER_WINDOW,
)
from tests.logic.tool.runner import run_suite

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tool-call regression test harness")
    add_connection_args(parser)
    parser.add_argument(
        "--gender",
        default=DEFAULT_GENDER,
        help=f"Assistant gender (default: {DEFAULT_GENDER})",
    )
    parser.add_argument(
        "--personality",
        default=DEFAULT_PERSONALITY,
        help=f"Assistant personality (default: {DEFAULT_PERSONALITY})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Per-response timeout in seconds (default: 20)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of test cases to run in parallel (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit on number of test cases to run",
    )
    parser.add_argument(
        "--show-successes",
        action="store_true",
        help="Include passing test cases in the per-case output",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=TOOL_WS_MAX_MESSAGES_PER_WINDOW,
        help=(
            "Skip tool cases with more steps than this limit "
            f"(default: {TOOL_WS_MAX_MESSAGES_PER_WINDOW}; 0 disables the filter)"
        ),
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    try:
        ws_url = with_api_key(args.server, api_key=args.api_key)
    except ValueError as exc:
        print(f"[error] {exc}")
        sys.exit(1)

    try:
        results = asyncio.run(
            run_suite(
                ws_url=ws_url,
                gender=args.gender or DEFAULT_GENDER,
                personality=args.personality or DEFAULT_PERSONALITY,
                timeout_s=max(0.1, args.timeout),
                concurrency=max(1, args.concurrency),
                limit=args.limit,
                show_successes=args.show_successes,
                max_steps_per_case=args.max_steps,
            )
        )
        # Exit with error if any test failed
        if any(not r.success for r in results):
            sys.exit(1)
    except KeyboardInterrupt:
        print("Interrupted.")


if __name__ == "__main__":
    main()
