#!/usr/bin/env python3
"""
Warmup client: connects to the local FastAPI websocket, sends a start message
with a random prompt, prints ACK, collects full response, and reports metrics.

Metrics reported:
- ttfb_ms: time from request send to first token
- total_ms: time from request send to done
- stream_ms: time from first token to done
- chunks: number of token messages received
- chars: size of final response (characters)
- first_3_words_ms: time from request send to first three words

Usage:
  python3 test/warmup.py
  python3 test/warmup.py "your custom message"
  python3 test/warmup.py --gender male --style playful "hello there"

Env:
  SERVER_WS_URL=ws://127.0.0.1:8000/ws
  YAP_API_KEY=yap_token (or your custom API key)
  ASSISTANT_GENDER=female|male
  PERSONA_STYLE=flirty

Note: API key authentication is required. The client will automatically
append the API key as a query parameter to the WebSocket URL.
"""

from __future__ import annotations

import argparse
import asyncio


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("message", nargs="*", help="optional user message")
    parser.add_argument(
        "--assistant-gender",
        "--gender",
        "-g",
        dest="assistant_gender",
        choices=["female", "male", "woman", "man"],
        help="assistant gender (normalized by server)",
    )
    parser.add_argument(
        "--persona-style",
        "--style",
        "-s",
        dest="persona_style",
        help="persona style (e.g., wholesome, savage, playful)",
    )
    return parser.parse_args()


async def _run_once(args: argparse.Namespace) -> None:
    from warmup.runner import run_once

    await run_once(args)


def main() -> None:
    args = _parse_args()
    try:
        asyncio.run(_run_once(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()