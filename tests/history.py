#!/usr/bin/env python3
"""History recall test for warm history and prefix caching.

Connects to the WebSocket server with a pre-built conversation history, then
sends follow-up messages to test the assistant's recall of earlier exchanges.
Tracks TTFB for each response and prints summary statistics (p50, p90, p95).

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- TEXT_API_KEY: API key for authentication (required, no default)
- GENDER: female|male (default: female)
- PERSONALITY: personality (default: flirty)

Usage:
  python3 tests/history.py
  python3 tests/history.py --gender male
  python3 tests/history.py --temperature 0.8 --top_p 0.9
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.setup import setup_repo_path
from tests.helpers.cli import (
    add_connection_args,
    add_sampling_args,
    build_sampling_payload,
)
from tests.helpers.errors import ServerError
from tests.config import (
    DEFAULT_SERVER_WS_URL,
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
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
        choices=["female", "male", "woman", "man"],
        default=os.getenv("GENDER", DEFAULT_GENDER),
        help="gender (normalized by server)",
    )
    parser.add_argument(
        "--personality",
        dest="personality",
        default=os.getenv("PERSONALITY", DEFAULT_PERSONALITY),
        help="personality (e.g., wholesome, savage, flirty)",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    """Thin orchestrator: parse CLI args and run the test."""
    setup_repo_path()
    from tests.logic.history.runner import run_test

    args = _parse_args()
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


if __name__ == "__main__":
    main()
