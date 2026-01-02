#!/usr/bin/env python3
"""
Personality switch WS test.

Tests the ability to dynamically switch persona/chat_prompt mid-session.
Cycles through 5 personalities (flirty, savage, religious, delulu, spiritual)
alternating between genders while maintaining conversation history.

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
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.helpers.setup import setup_repo_path
from tests.helpers.cli import (
    add_connection_args,
    add_sampling_args,
    build_sampling_payload,
)
from tests.helpers.errors import ServerError
from tests.config import (
    DEFAULT_SERVER_WS_URL,
    PERSONALITY_PERSONA_VARIANTS,
    PERSONALITY_SWITCH_DEFAULT,
    PERSONALITY_SWITCH_DELAY_SECONDS,
    PERSONALITY_SWITCH_MAX,
    PERSONALITY_SWITCH_MIN,
    PERSONALITY_REPLIES_PER_SWITCH,
    PERSONALITY_NAME_CHECK_MESSAGE,
    PERSONALITY_CONVERSATION_MESSAGES,
)
from tests.logic.persona import run_persona_test, PersonaSwitchConfig


def _build_config() -> PersonaSwitchConfig:
    """Build configuration for personality switch tests."""
    return PersonaSwitchConfig(
        test_name="PERSONALITY SWITCH TEST",
        prompts=tuple(PERSONALITY_CONVERSATION_MESSAGES),
        name_check_message=PERSONALITY_NAME_CHECK_MESSAGE,
        variants=tuple(PERSONALITY_PERSONA_VARIANTS),
        replies_per_switch=PERSONALITY_REPLIES_PER_SWITCH,
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


async def run_test(
    ws_url: str,
    api_key: str | None,
    switches: int,
    delay_s: int,
    sampling: dict[str, float | int] | None,
) -> None:
    """Run the personality switch test."""
    config = _build_config()
    await run_persona_test(
        ws_url=ws_url,
        api_key=api_key,
        config=config,
        switches=switches,
        delay_s=delay_s,
        sampling=sampling,
    )


def main() -> None:
    """Parse CLI args and run the test."""
    setup_repo_path()
    args = _parse_args()
    switches = max(PERSONALITY_SWITCH_MIN, min(PERSONALITY_SWITCH_MAX, args.switches))
    try:
        asyncio.run(
            run_test(
                args.server,
                args.api_key,
                switches,
                args.delay,
                args.sampling or None,
            )
        )
    except ServerError:
        sys.exit(1)


if __name__ == "__main__":
    main()
