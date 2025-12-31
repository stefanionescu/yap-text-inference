#!/usr/bin/env python3
"""WebSocket connection lifecycle CLI tester."""

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
from tests.helpers.ws import with_api_key
from tests.config import (
    CONNECTION_NORMAL_WAIT_SECONDS,
    CONNECTION_IDLE_EXPECT_SECONDS,
    CONNECTION_IDLE_GRACE_SECONDS,
)
from tests.logic.connections import run_connection_suite


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WebSocket connection lifecycle tester")
    add_connection_args(
        parser,
        server_help="Base WebSocket URL (defaults to SERVER_WS_URL env)",
    )
    parser.add_argument(
        "--normal-wait",
        type=float,
        default=CONNECTION_NORMAL_WAIT_SECONDS,
        help=(
            "Seconds to keep the normal connection open before sending the end frame "
            f"(default: {CONNECTION_NORMAL_WAIT_SECONDS})"
        ),
    )
    parser.add_argument(
        "--idle-expect-seconds",
        type=float,
        default=CONNECTION_IDLE_EXPECT_SECONDS,
        help=(
            "Seconds to wait for the server's idle watchdog to close a connection. "
            "Defaults to CONNECTION_IDLE_EXPECT_SECONDS or WS_IDLE_TIMEOUT_S."
        ),
    )
    parser.add_argument(
        "--idle-grace-seconds",
        type=float,
        default=CONNECTION_IDLE_GRACE_SECONDS,
        help=(
            "Additional buffer added to the idle wait window before failing. "
            f"Default: {CONNECTION_IDLE_GRACE_SECONDS}"
        ),
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
        run_connection_suite(
            ws_url,
            normal_wait_s=args.normal_wait,
            idle_expect_s=args.idle_expect_seconds,
            idle_grace_s=args.idle_grace_seconds,
        )
    )
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
