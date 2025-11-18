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
  TEXT_API_KEY=yap_token
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import uuid

import websockets


ANALYSIS_TEXT = (
    "The screenshot shows a calendar with two meetings at 10:00 and 14:00, "
    "plus a reminder to email Alex."
)


def _with_api_key(url: str, env: str = "TEXT_API_KEY", default_key: str = "yap_token") -> str:
    key = os.getenv(env, default_key)
    return f"{url}&api_key={key}" if "?" in url else f"{url}?api_key={key}"


async def _send_client_end(ws) -> None:
    with contextlib.suppress(Exception):
        await ws.send(json.dumps({"type": "end"}))


async def run_once() -> None:
    url = os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws")
    ws_url = _with_api_key(url)

    session_id = str(uuid.uuid4())

    # Message intended to trigger screenshot decision
    start_payload = {
        "type": "start",
        "session_id": session_id,
        "assistant_gender": "female",
        "personality": "flirty",
        "history_text": "",
        "user_utterance": "look at this — what do you think?",
    }

    async with websockets.connect(ws_url, max_queue=None) as ws:
        try:
            await ws.send(json.dumps(start_payload))

            saw_tool_yes = False
            short_text = ""

            # Phase 1: observe toolcall & first answer
            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                t = msg.get("type")

                if t == "ack":
                    continue

                if t == "toolcall":
                    print("TOOLCALL:", msg)
                    status = (msg.get("status") or "").lower()
                    if status != "yes":
                        raise RuntimeError(f"Expected toolcall 'yes', got '{status}'")
                    saw_tool_yes = True
                    continue

                if t == "token":
                    piece = msg.get("text", "")
                    short_text += piece
                    continue

                if t == "final":
                    if msg.get("normalized_text"):
                        short_text = msg["normalized_text"]
                    continue

                if t == "done":
                    break

                if t == "error":
                    raise RuntimeError(msg)

            print("First reply:", short_text)
            if not saw_tool_yes:
                raise RuntimeError("Did not receive toolcall 'yes'")

            # Phase 2: send followup with fake analysis
            followup_payload = {
                "type": "followup",
                "analysis_text": ANALYSIS_TEXT,
                "history_text": "",
            }
            await ws.send(json.dumps(followup_payload))

            final2 = ""
            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                t = msg.get("type")
                if t == "token":
                    final2 += msg.get("text", "")
                    continue
                if t == "final":
                    if msg.get("normalized_text"):
                        final2 = msg["normalized_text"]
                    continue
                if t == "done":
                    break
                if t == "error":
                    raise RuntimeError(msg)

            print("PHASE2 FOLLOWUP FINAL (trunc):", final2[:240])
        finally:
            await _send_client_end(ws)


if __name__ == "__main__":
    asyncio.run(run_once())


