#!/usr/bin/env python3
"""
Tool model regression tester CLI.

Parses command-line arguments and defers execution to tool.runner.
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

setup_repo_path()

from tests.helpers.cli import add_connection_args, add_prompt_mode_arg  # noqa: E402
from tests.helpers.ws import with_api_key  # noqa: E402
from tests.config import DEFAULT_GENDER, DEFAULT_PERSONALITY  # noqa: E402
from tests.logic.tool.runner import run_suite  # noqa: E402
from tests.logic.tool.prompts import (  # noqa: E402
    DEFAULT_TOOL_PROMPT_NAME,
    ToolPromptRegistry,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Tool-call regression test harness")
    add_connection_args(parser)
    add_prompt_mode_arg(parser)
    parser.add_argument(
        "--gender",
        default=DEFAULT_GENDER,
        help=f"Assistant gender (default: {DEFAULT_GENDER})",
    )
    parser.add_argument(
        "--personality",
        default=DEFAULT_PERSONALITY,
        help=f"Assistant personality (default: {DEFAULT_PERSONALITY})",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=5.0,
        help="Per-response timeout in seconds (default: 5)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=1,
        help="Number of test cases to run in parallel (default: 1)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Optional limit on number of test cases to run",
    )
    parser.add_argument(
        "--show-successes",
        action="store_true",
        help="Include passing test cases in the per-case output",
    )
    parser.add_argument(
        "--tool-prompt",
        default=DEFAULT_TOOL_PROMPT_NAME,
        help=f"Tool prompt name defined in tests/prompts/toolcall.py (default: {DEFAULT_TOOL_PROMPT_NAME})",
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()

    try:
        ws_url = with_api_key(args.server, api_key=args.api_key)
    except ValueError as exc:
        print(f"[error] {exc}")
        sys.exit(1)

    registry = ToolPromptRegistry()
    try:
        prompt_definition = registry.require(args.tool_prompt)
    except ValueError as exc:
        print(f"[error] {exc}")
        sys.exit(1)

    try:
        asyncio.run(
            run_suite(
                ws_url=ws_url,
                gender=args.gender or DEFAULT_GENDER,
                personality=args.personality or DEFAULT_PERSONALITY,
                tool_prompt=prompt_definition.prompt,
                timeout_s=max(0.1, args.timeout),
                concurrency=max(1, args.concurrency),
                limit=args.limit,
                show_successes=args.show_successes,
                prompt_mode=args.prompt_mode,
            )
        )
    except KeyboardInterrupt:
        print("Interrupted.")


if __name__ == "__main__":
    main()

