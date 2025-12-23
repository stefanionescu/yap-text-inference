#!/usr/bin/env python3
"""
Warmup client: connects to the local FastAPI websocket, sends a start message
with a random prompt, prints ACK, collects full response, and reports metrics.

Metrics reported:
- ttfb_ms: time from request send to first token
- total_ms: time from request send to done
- stream_ms: time from first token to done
- chunks: number of token messages received
- chars: size of final response (characters)
- first_3_words_ms: time from request send to first three words

Usage:
  python3 tests/warmup.py
  python3 tests/warmup.py "your custom message"
  python3 tests/warmup.py --gender male --style playful "hello there"

Env:
  SERVER_WS_URL=ws://127.0.0.1:8000/ws
  TEXT_API_KEY=your_api_key (required, no default)
  GENDER=female|male
  PERSONALITY=flirty

Note: API key authentication is required. The client will automatically
append the API key as a query parameter to the WebSocket URL.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.setup import setup_repo_path

setup_repo_path()

from tests.helpers.cli import (
    add_connection_args,
    add_chat_prompt_arg,
    add_sampling_args,
    build_sampling_payload,
)
from tests.logic.warmup.runner import run_once


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("message", nargs="*", help="optional user message")

    add_connection_args(parser)
    add_sampling_args(parser)
    add_chat_prompt_arg(parser)

    parser.add_argument(
        "--gender",
        dest="gender",
        choices=["female", "male", "woman", "man"],
        help="gender (normalized by server)",
    )
    parser.add_argument(
        "--personality",
        dest="personality",
        help="personality (e.g., wholesome, savage, playful)",
    )
    parser.add_argument(
        "--double-ttfb",
        action="store_true",
        help="send two sequential start messages over one connection and log metrics per transaction",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    try:
        asyncio.run(run_once(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
