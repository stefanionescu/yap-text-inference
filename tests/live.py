#!/usr/bin/env python3
"""
Interactive live WebSocket test client.

- Starts a session using the same default prompt as warmup (anna_flirty)
- Keeps the connection open so you can exchange messages from the CLI
    - Supports hot-reloading persona definitions from `tests/prompts/detailed.py`
- Lets you switch personas mid-session via `chat_prompt` updates
- Prints streaming tokens, metrics, and structured error information
- Sends a graceful `{"type": "end"}` message on /stop, Ctrl+C, or server close
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import uuid
import sys
from pathlib import Path

import websockets  # type: ignore[import-not-found]

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.setup import setup_repo_path
from tests.config import (
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from tests.helpers.cli import (
    add_connection_args,
    add_sampling_args,
    build_sampling_payload,
)
from tests.helpers.ws import connect_with_retries, with_api_key
from tests.helpers.errors import IdleTimeoutError
from tests.logic.live import (
    DEFAULT_PERSONA_NAME,
    LiveClient,
    LiveConnectionClosed,
    LiveIdleTimeout,
    LiveServerError,
    LiveSession,
    PersonaRegistry,
)
from tests.logic.live.cli import interactive_loop, print_help

logger = logging.getLogger("live")


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
        "--recv-timeout",
        dest="recv_timeout",
        type=float,
        default=DEFAULT_RECV_TIMEOUT_SEC,
        help=f"Receive timeout in seconds (default: {DEFAULT_RECV_TIMEOUT_SEC})",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


async def _run(args: argparse.Namespace) -> None:
    registry = PersonaRegistry()
    try:
        persona = registry.require(args.persona)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    initial_message = (
        " ".join(args.message).strip() if args.message else "Hey!"
    )

    session = LiveSession(
        session_id=f"live-{uuid.uuid4()}",
        persona=persona,
        include_chat_prompt=True,
        sampling=args.sampling or None,
    )

    # Print interactive banner before any assistant output
    print_help(persona.name)

    ws_url = with_api_key(args.server, api_key=args.api_key)
    try:
        async with connect_with_retries(
            lambda: websockets.connect(
                ws_url,
                max_queue=None,
                ping_interval=DEFAULT_WS_PING_INTERVAL,
                ping_timeout=DEFAULT_WS_PING_TIMEOUT,
            )
        ) as ws:
            client = LiveClient(ws, session, args.recv_timeout)
            try:
                await client.send_initial_message(initial_message)
                await interactive_loop(client, registry, show_banner=False)
            finally:
                await client.close()
    except asyncio.TimeoutError:
        logger.error("Timed out while connecting to %s", args.server)
        raise SystemExit(1) from None
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
        close_code = getattr(exc, "code", None)
        close_reason = getattr(exc, "reason", None)
        if close_code == 4000 or (close_reason and "idle" in str(close_reason).lower()):
            logger.info("Session ended due to inactivity. Goodbye!")
        else:
            logger.warning("Server closed the connection (code=%s). Exiting.", close_code)
    except (IdleTimeoutError, LiveIdleTimeout):
        logger.info("Session ended due to inactivity. Goodbye!")
    except LiveServerError as exc:
        if exc.code == "authentication_failed":
            logger.error(
                "Authentication failed: server rejected the provided API key. "
                "Double-check `--api-key` or `TEXT_API_KEY`."
            )
            raise SystemExit(1) from exc
        if exc.code == "server_at_capacity":
            logger.error("Server is busy. Please try again later.")
            raise SystemExit(1) from exc
        logger.error("Server error: %s", exc)
        raise SystemExit(1) from exc
    except LiveConnectionClosed as exc:
        logger.warning("Connection closed: %s", exc)
    except Exception:
        logger.exception("Unexpected error while running live client")


def main() -> None:
    setup_repo_path()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
