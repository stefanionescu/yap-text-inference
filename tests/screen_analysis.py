#!/usr/bin/env python3
"""
Screen analysis follow-up regression test CLI.

Parses command-line arguments and defers execution to screen_analysis.runner.

Flow:
 1) Connect to /ws and send a 'start' that should trigger toolcall YES.
 2) Observe 'toolcall' frame and streaming tokens/final from the first request.
 3) Send a 'followup' message with analysis text; expect a second streamed answer.
    This test requires toolcall == YES; if the decision is NO, the test fails.

Env:
  SERVER_WS_URL=ws://127.0.0.1:8000/ws
  TEXT_API_KEY=your_api_key (required, no default)
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
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_SERVER_WS_URL,
)
from tests.helpers.prompt import select_chat_prompt


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Screen analysis follow-up regression test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def main() -> None:
    """Run the screen analysis flow test."""
    setup_repo_path()
    from tests.logic.screen_analysis import run_once

    args = _parse_args()
    chat_prompt = select_chat_prompt(DEFAULT_GENDER)

    asyncio.run(
        run_once(
            args.server,
            args.api_key,
            args.sampling or None,
            chat_prompt,
        )
    )


if __name__ == "__main__":
    main()
