#!/usr/bin/env python3
"""
End-to-end exercise of toolcall → chat and follow-up (screen analysis) flow.

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
import json
import logging
import os
import sys
import uuid

import websockets

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tests.helpers.cli import add_connection_args, add_sampling_args, build_sampling_payload
from tests.helpers.message import iter_messages
from tests.helpers.ws import send_client_end, with_api_key
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from tests.messages.screen_analysis import SCREEN_ANALYSIS_TEXT, SCREEN_ANALYSIS_USER_REPLY
from tests.logic.tool.prompts import (
    DEFAULT_TOOL_PROMPT_NAME,
    ToolPromptRegistry,
)

logger = logging.getLogger(__name__)


async def _consume_initial_response(ws) -> tuple[bool, str]:
    saw_tool_yes = False
    short_text = ""
    async for msg in iter_messages(ws):
        t = msg.get("type")

        if t == "ack":
            continue
        if t == "toolcall":
            status = (msg.get("status") or "").lower()
            logger.info("TOOLCALL: %s", msg)
            if status != "yes":
                raise RuntimeError(f"Expected toolcall 'yes', got '{status}'")
            saw_tool_yes = True
            continue
        if t == "token":
            short_text += msg.get("text", "")
            continue
        if t == "final":
            if msg.get("normalized_text"):
                short_text = msg["normalized_text"]
            continue
        if t == "done":
            break
        if t == "error":
            raise RuntimeError(msg)
    return saw_tool_yes, short_text


async def _consume_followup(ws) -> str:
    final_text = ""
    async for msg in iter_messages(ws):
        t = msg.get("type")
        if t == "token":
            final_text += msg.get("text", "")
            continue
        if t == "final":
            if msg.get("normalized_text"):
                final_text = msg["normalized_text"]
            continue
        if t == "done":
            break
        if t == "error":
            raise RuntimeError(msg)
    return final_text


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Screen analysis follow-up regression test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
    parser.add_argument(
        "--tool-prompt",
        default=DEFAULT_TOOL_PROMPT_NAME,
        help=f"Tool prompt name defined in tests/prompts/toolcall.py (default: {DEFAULT_TOOL_PROMPT_NAME})",
    )
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


async def run_once(
    server: str,
    api_key: str | None,
    sampling: dict[str, float | int] | None,
    tool_prompt: str,
) -> None:
    ws_url = with_api_key(server, api_key=api_key)
    session_id = str(uuid.uuid4())

    start_payload = {
        "type": "start",
        "session_id": session_id,
        "gender": DEFAULT_GENDER,
        "personality": DEFAULT_PERSONALITY,
        "history_text": "",
        "user_utterance": SCREEN_ANALYSIS_USER_REPLY,
        "tool_prompt": tool_prompt,
    }
    if sampling:
        start_payload["sampling"] = sampling

    async with websockets.connect(
        ws_url,
        max_queue=None,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            await ws.send(json.dumps(start_payload))
            saw_tool_yes, short_text = await _consume_initial_response(ws)
            logger.info("First reply: %s", short_text)
            if not saw_tool_yes:
                raise RuntimeError("Did not receive toolcall 'yes'")

            followup_payload = {
                "type": "followup",
                "analysis_text": SCREEN_ANALYSIS_TEXT,
                "history_text": "",
            }
            await ws.send(json.dumps(followup_payload))
            final_followup = await _consume_followup(ws)
            logger.info("PHASE2 FOLLOWUP FINAL (trunc): %s", final_followup[:240])
        finally:
            await send_client_end(ws)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    args = _parse_args()
    registry = ToolPromptRegistry()
    try:
        prompt_definition = registry.require(args.tool_prompt)
    except ValueError as exc:
        print(f"[error] {exc}")
        raise SystemExit(1) from exc

    asyncio.run(run_once(args.server, args.api_key, args.sampling or None, prompt_definition.prompt))


