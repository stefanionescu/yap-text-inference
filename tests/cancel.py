#!/usr/bin/env python3
"""Cancel request test: verifies cancel aborts in-flight requests and
subsequent requests complete successfully.

This test validates the cancel message handling by:
1. Sending a start message to begin generation
2. Sending a cancel message immediately after ACK
3. Verifying the done response has cancelled=True
4. Waiting a short period, then sending another request
5. Verifying the recovery request completes successfully

The test works with all deployment modes (tool only, chat only, or both).

Usage:
  python3 tests/cancel.py
  python3 tests/cancel.py --server ws://localhost:8000/ws
  python3 tests/cancel.py --post-cancel-wait 3.0 --timeout 60

Env:
  SERVER_WS_URL=ws://127.0.0.1:8000/ws
  TEXT_API_KEY=your_api_key (required, no default)
  GENDER=female|male
  PERSONALITY=flirty
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
from tests.helpers.cli import add_connection_args
from tests.helpers.websocket import with_api_key
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    CANCEL_POST_WAIT_DEFAULT,
    CANCEL_RECV_TIMEOUT_DEFAULT,
)
from tests.logic.cancel import run_cancel_suite


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cancel request test: verifies cancel and recovery behavior"
    )
    add_connection_args(
        parser,
        server_help="Base WebSocket URL (defaults to SERVER_WS_URL env)",
    )
    parser.add_argument(
        "--post-cancel-wait",
        type=float,
        default=CANCEL_POST_WAIT_DEFAULT,
        help=(
            "Seconds to wait after cancel before sending recovery request "
            f"(default: {CANCEL_POST_WAIT_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=CANCEL_RECV_TIMEOUT_DEFAULT,
        help=(
            "Receive timeout for each phase in seconds "
            f"(default: {CANCEL_RECV_TIMEOUT_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--gender",
        choices=["female", "male"],
        default=DEFAULT_GENDER,
        help=f"Persona gender (default: {DEFAULT_GENDER})",
    )
    parser.add_argument(
        "--personality",
        default=DEFAULT_PERSONALITY,
        help=f"Persona personality style (default: {DEFAULT_PERSONALITY})",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    setup_repo_path()
    args = _parse_args()
    logging.basicConfig(level=getattr(logging, args.log_level), format="%(message)s")

    try:
        ws_url = with_api_key(args.server, api_key=args.api_key)
    except ValueError as exc:
        logging.error("%s", exc)
        sys.exit(1)

    ok = asyncio.run(
        run_cancel_suite(
            ws_url,
            gender=args.gender,
            personality=args.personality,
            post_cancel_wait_s=args.post_cancel_wait,
            recv_timeout_s=args.timeout,
        )
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
