#!/usr/bin/env python3
"""
Interactive live WebSocket test client.

- Starts a session using the same default prompt as warmup (anna_flirty)
- Keeps the connection open so you can exchange messages from the CLI
- Supports hot-reloading persona definitions from `test/prompts/live.py`
- Lets you switch personas mid-session via `chat_prompt` updates
- Prints streaming tokens, metrics, and structured error information
- Sends a graceful `{"type": "end"}` message on /stop, Ctrl+C, or server close
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import uuid

import websockets  # type: ignore[import-not-found]

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from test.common.cli import add_connection_args
from test.common.util import choose_message
from test.common.ws import with_api_key
from test.config import (
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    WARMUP_DEFAULT_MESSAGES,
    WARMUP_FALLBACK_MESSAGE,
)
from test.live import (
    DEFAULT_PERSONA_NAME,
    LiveClient,
    LiveSession,
    PersonaRegistry,
)
from test.live.cli import interactive_loop

logger = logging.getLogger("live")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Interactive live chat WebSocket test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
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
        help=f"Persona name from test/prompts/live.py (default: {DEFAULT_PERSONA_NAME})",
    )
    parser.add_argument(
        "--recv-timeout",
        dest="recv_timeout",
        type=float,
        default=DEFAULT_RECV_TIMEOUT_SEC,
        help=f"Receive timeout in seconds (default: {DEFAULT_RECV_TIMEOUT_SEC})",
    )
    return parser.parse_args()


async def _run(args: argparse.Namespace) -> None:
    registry = PersonaRegistry()
    try:
        persona = registry.require(args.persona)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    initial_message = choose_message(
        args.message,
        fallback=WARMUP_FALLBACK_MESSAGE,
        defaults=WARMUP_DEFAULT_MESSAGES,
    )

    session = LiveSession(
        session_id=f"live-{uuid.uuid4()}",
        persona=persona,
    )

    ws_url = with_api_key(args.server, api_key=args.api_key)
    logger.info("Connecting to %s", args.server)
    try:
        async with websockets.connect(
            ws_url,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        ) as ws:
            client = LiveClient(ws, session, args.recv_timeout)
            try:
                await client.send_initial_message(initial_message)
                await interactive_loop(client, registry)
            finally:
                await client.close()
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
        logger.warning("Server closed the connection. Exiting.")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    try:
        asyncio.run(_run(args))
    except KeyboardInterrupt:
        logger.info("Interrupted by user")


if __name__ == "__main__":
    main()


