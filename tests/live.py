#!/usr/bin/env python3
"""Interactive live WebSocket test client.

- Starts a session using the same default prompt as warmup (anna_flirty)
- Keeps the connection open so you can exchange messages from the CLI
    - Supports hot-reloading persona definitions from `tests/prompts/detailed.py`
- Lets you select personas from `tests/prompts/detailed.py` via the `--persona` flag
- Prints streaming tokens, metrics, and structured error information
- Sends a graceful `{"type": "end"}` message on /stop, Ctrl+C, or server close
"""

from __future__ import annotations

import asyncio
import logging
import argparse

try:
    from tests.helpers.setup import setup_repo_path
except ModuleNotFoundError:
    from helpers.setup import setup_repo_path  # type: ignore[import-not-found]

setup_repo_path()

from tests.logic.live import DEFAULT_PERSONA_NAME  # noqa: E402
from tests.config import DEFAULT_SERVER_WS_URL, DEFAULT_RECV_TIMEOUT_SEC  # noqa: E402
from tests.helpers.cli import add_sampling_args, add_connection_args, build_sampling_payload  # noqa: E402


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive live chat WebSocket test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    parser.add_argument(
        "message",
        nargs="*",
        help="optional opener message (defaults to warmup fallback/random)",
    )
    parser.add_argument(
        "--persona",
        "-p",
        dest="persona",
        default=DEFAULT_PERSONA_NAME,
        help=f"Persona name from tests/prompts/detailed.py (default: {DEFAULT_PERSONA_NAME})",
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=DEFAULT_RECV_TIMEOUT_SEC,
        help=f"Receive timeout in seconds (default: {DEFAULT_RECV_TIMEOUT_SEC})",
    )
    parser.add_argument(
        "--warm",
        action="store_true",
        help="Start with pre-built conversation history for testing recall",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    from tests.logic.live import run  # noqa: PLC0415

    asyncio.run(
        run(
            server_url=args.server,
            api_key=args.api_key,
            persona_name=args.persona,
            timeout=args.timeout,
            sampling=args.sampling or None,
            warm=args.warm,
            message=args.message,
        )
    )


if __name__ == "__main__":
    main()
