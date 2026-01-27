#!/usr/bin/env python3
"""
Conversation history tester.

Opens a websocket session, reuses a single persona, and replays a scripted
ten-turn conversation to verify that history retention and KV-cache behavior
remain stable under bounded-history constraints. Each exchange logs:
  - user + assistant text
  - time to first token (TTFB)
  - time to first three words
  - time to first complete sentence

Usage:
    python3 tests/conversation.py
    python3 tests/conversation.py --server ws://127.0.0.1:8000/ws
"""

from __future__ import annotations

import sys
import asyncio
import logging
import argparse
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.errors import ServerError
from tests.helpers.setup import setup_repo_path
from tests.logic.conversation import run_conversation
from tests.messages.conversation import CONVERSATION_HISTORY_MESSAGES
from tests.helpers.cli import add_sampling_args, add_connection_args, build_sampling_payload
from tests.config import DEFAULT_GENDER, DEFAULT_PERSONALITY, DEFAULT_SERVER_WS_URL, DEFAULT_RECV_TIMEOUT_SEC


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conversation history regression test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    parser.add_argument(
        "--gender",
        dest="gender",
        help="Assistant gender override (defaults to env/DEFAULT_GENDER)",
    )
    parser.add_argument(
        "--personality",
        dest="personality",
        help="Assistant personality override (defaults to env/DEFAULT_PERSONALITY)",
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


def main() -> None:
    setup_repo_path()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    gender = args.gender or DEFAULT_GENDER
    personality = args.personality or DEFAULT_PERSONALITY
    try:
        asyncio.run(
            run_conversation(
                ws_url=args.server,
                api_key=args.api_key,
                prompts=CONVERSATION_HISTORY_MESSAGES,
                gender=gender,
                personality=personality,
                recv_timeout=args.recv_timeout,
                sampling=args.sampling or None,
            )
        )
    except ServerError:
        sys.exit(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
