#!/usr/bin/env python3
"""Cancel request test: verifies cancel aborts in-flight requests and
subsequent requests complete successfully.

This test validates the cancel message handling using multiple concurrent clients:
1. Multiple clients (default 3) connect simultaneously
2. One client sends a start message, waits ~1s collecting tokens, then cancels
3. That client verifies done with cancelled=True, then verifies no spurious messages
4. That client sends a recovery request and completes it
5. The other clients complete their inference normally
6. All clients wait for the canceling client's recovery before finishing

The test works with all deployment modes (tool only, chat only, or both).

Usage:
  python3 tests/cancel.py
  python3 tests/cancel.py --server ws://localhost:8000/ws
  python3 tests/cancel.py --clients 3 --cancel-delay 1.0 --drain-timeout 2.0

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
    CANCEL_NUM_CLIENTS_DEFAULT,
    CANCEL_DELAY_BEFORE_CANCEL_DEFAULT,
    CANCEL_DRAIN_TIMEOUT_DEFAULT,
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
        "--clients",
        type=int,
        default=CANCEL_NUM_CLIENTS_DEFAULT,
        help=(
            "Number of concurrent clients (1 cancels, rest complete normally) "
            f"(default: {CANCEL_NUM_CLIENTS_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--cancel-delay",
        type=float,
        default=CANCEL_DELAY_BEFORE_CANCEL_DEFAULT,
        help=(
            "Seconds to wait after start before sending cancel "
            f"(default: {CANCEL_DELAY_BEFORE_CANCEL_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--drain-timeout",
        type=float,
        default=CANCEL_DRAIN_TIMEOUT_DEFAULT,
        help=(
            "Seconds to verify no spurious messages after cancel "
            f"(default: {CANCEL_DRAIN_TIMEOUT_DEFAULT})"
        ),
    )
    parser.add_argument(
        "--post-cancel-wait",
        type=float,
        default=CANCEL_POST_WAIT_DEFAULT,
        help=(
            "Seconds to wait after drain before sending recovery request "
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
            num_clients=args.clients,
            cancel_delay_s=args.cancel_delay,
            drain_timeout_s=args.drain_timeout,
            post_cancel_wait_s=args.post_cancel_wait,
            recv_timeout_s=args.timeout,
        )
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
