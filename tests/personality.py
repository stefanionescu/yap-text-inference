#!/usr/bin/env python3
"""
Personality switch WS test.

Tests the ability to dynamically switch persona/chat_prompt mid-session.
Cycles through PERSONA_VARIANTS while maintaining conversation history.

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- TEXT_API_KEY: API key for authentication (required, no default)
- CHAT_PROMPT_UPDATE_WINDOW_SECONDS: Rate limit window for persona updates
- CHAT_PROMPT_UPDATE_MAX_PER_WINDOW: Max updates per window
- WS_MESSAGE_WINDOW_SECONDS: Rate limit window for messages
- WS_MAX_MESSAGES_PER_WINDOW: Max messages per window

Usage:
  python3 tests/personality.py
  python3 tests/personality.py --switches 5 --delay 2
  python3 tests/personality.py --temperature 0.8 --top_p 0.9
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tests.helpers.cli import add_connection_args, add_sampling_args, build_sampling_payload
from tests.config import (
    DEFAULT_SERVER_WS_URL,
    PERSONALITY_SWITCH_DEFAULT,
    PERSONALITY_SWITCH_DELAY_SECONDS,
    PERSONALITY_SWITCH_MAX,
    PERSONALITY_SWITCH_MIN,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Personality switch WS test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    parser.add_argument(
        "--switches",
        dest="switches",
        type=int,
        default=PERSONALITY_SWITCH_DEFAULT,
        help=f"Number of chat prompt switches ({PERSONALITY_SWITCH_MIN}-{PERSONALITY_SWITCH_MAX}), "
        f"default {PERSONALITY_SWITCH_DEFAULT}",
    )
    parser.add_argument(
        "--delay",
        dest="delay",
        type=int,
        default=PERSONALITY_SWITCH_DELAY_SECONDS,
        help=f"Seconds between switches (default {PERSONALITY_SWITCH_DELAY_SECONDS})",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    """Thin orchestrator: parse CLI args and run the test."""
    from tests.logic.personality.runner import run_test

    args = _parse_args()
    switches = max(PERSONALITY_SWITCH_MIN, min(PERSONALITY_SWITCH_MAX, args.switches))
    asyncio.run(run_test(args.server, args.api_key, switches, args.delay, args.sampling or None))


if __name__ == "__main__":
    main()

