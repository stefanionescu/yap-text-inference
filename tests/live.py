#!/usr/bin/env python3
"""
Interactive live WebSocket test client.

- Starts a session using the same default prompt as warmup (anna_flirty)
- Keeps the connection open so you can exchange messages from the CLI
    - Supports hot-reloading persona definitions from `tests/prompts/live.py`
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

setup_repo_path()

from tests.config import (
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from tests.helpers.cli import (
    add_connection_args,
    add_prompt_mode_arg,
    add_sampling_args,
    build_sampling_payload,
)
from tests.helpers.ws import connect_with_retries, with_api_key
from tests.logic.live import (
    DEFAULT_PERSONA_NAME,
    LiveClient,
    LiveConnectionClosed,
    LiveServerError,
    LiveSession,
    PersonaRegistry,
)
from tests.helpers.prompt import (
    PROMPT_MODE_BOTH,
    select_tool_prompt,
    should_send_chat_prompt,
    should_send_tool_prompt,
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
    add_prompt_mode_arg(parser)
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
        help=f"Persona name from tests/prompts/live.py (default: {DEFAULT_PERSONA_NAME})",
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

    prompt_mode = args.prompt_mode or PROMPT_MODE_BOTH
    chat_enabled = should_send_chat_prompt(prompt_mode)
    tool_prompt = select_tool_prompt() if should_send_tool_prompt(prompt_mode) else None
    if not chat_enabled and tool_prompt is None:
        raise SystemExit("prompt_mode must allow chat, tool, or both prompts for live testing.")
    if not chat_enabled:
        logger.warning(
            "Chat prompts disabled by prompt mode; persona changes and chat streaming will be limited."
        )

    session = LiveSession(
        session_id=f"live-{uuid.uuid4()}",
        persona=persona,
        include_chat_prompt=chat_enabled,
        tool_prompt=tool_prompt,
        sampling=args.sampling or None,
    )

    # Print interactive banner before any assistant output
    print_help(registry.available_names(), persona.name)

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
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
        logger.warning("Server closed the connection. Exiting.")
    except LiveServerError as exc:
        if exc.code == "authentication_failed":
            logger.error(
                "Authentication failed: server rejected the provided API key. "
                "Double-check `--api-key` or `TEXT_API_KEY`."
            )
            raise SystemExit(1) from exc
        logger.error("Server error: %s", exc)
        raise SystemExit(1) from exc
    except LiveConnectionClosed as exc:
        logger.warning("Connection closed: %s", exc)
    except Exception:
        logger.exception("Unexpected error while running live client")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()


