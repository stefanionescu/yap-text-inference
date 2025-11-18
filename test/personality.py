import argparse
import asyncio
import json
import os
import sys
import uuid
from typing import List, Tuple

import websockets

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from test.common.message import iter_messages
from test.common.ws import send_client_end, with_api_key
from test.config import (
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    PERSONA_SWITCH_REPLIES,
    PERSONA_VARIANTS,
    PERSONALITY_REPLIES_PER_SWITCH,
    PERSONALITY_SWITCH_DEFAULT,
    PERSONALITY_SWITCH_DELAY_SECONDS,
    PERSONALITY_SWITCH_MAX,
    PERSONALITY_SWITCH_MIN,
)
from test.prompts.toolcall import TOOLCALL_PROMPT


async def recv_until_done(ws) -> Tuple[str, List[dict]]:
    tokens = []
    final_text = ""
    toolcalls: List[dict] = []
    async for msg in iter_messages(ws):
        t = msg.get("type")
        if t == "token":
            tokens.append(msg.get("text", ""))
        elif t == "toolcall":
            toolcalls.append(msg)
        elif t == "final":
            final_text = msg.get("normalized_text", "")
        elif t == "done":
            break
        elif t == "error":
            raise RuntimeError(f"server error: {msg}")
    return final_text, toolcalls


async def send_start(ws, session_id: str, assistant_gender: str, personality: str, chat_prompt: str, tool_prompt: str, history_text: str, user_text: str) -> str:
    msg = {
        "type": "start",
        "session_id": session_id,
        "assistant_gender": assistant_gender,
        "personality": personality,
        "chat_prompt": chat_prompt,
        "tool_prompt": tool_prompt,
        "history_text": history_text,
        "user_utterance": user_text,
    }
    await (ws.send(json.dumps(msg)) if hasattr(ws, 'send') else ws.send(json.dumps(msg)))
    final_text, _ = await recv_until_done(ws)
    return final_text


async def send_update_chat_prompt(ws, session_id: str, assistant_gender: str, personality: str, chat_prompt: str, history_text: str) -> dict:
    msg = {
        "type": "chat_prompt",
        "session_id": session_id,
        "assistant_gender": assistant_gender,
        "personality": personality,
        "chat_prompt": chat_prompt,
        "history_text": history_text,
    }
    await ws.send(json.dumps(msg))
    # Wait for a single ack/error
    while True:
        ack = json.loads(await ws.recv())
        if ack.get("type") == "ack" and ack.get("for") == "chat_prompt":
            return ack
        if ack.get("type") == "error":
            return ack


async def run_test(ws_url: str, switches: int, delay_s: int) -> None:
    url = with_api_key(ws_url)
    session_id = f"sess-{uuid.uuid4()}"

    history_text = ""
    reply_idx = 0

    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            # Initial start with first variant and a simple opener
            variants = PERSONA_VARIANTS
            g0, p0, c0 = variants[0]
            opener = PERSONA_SWITCH_REPLIES[reply_idx % len(PERSONA_SWITCH_REPLIES)]
            reply_idx += 1
            final0 = await send_start(ws, session_id, g0, p0, c0, TOOLCALL_PROMPT, history_text, opener)
            history_text = f"User: {opener}\nAssistant: {final0}".strip()

            for i in range(switches):
                await asyncio.sleep(delay_s)
                g, p, c = variants[(i + 1) % len(variants)]

                ack = await send_update_chat_prompt(ws, session_id, g, p, c, history_text)
                # If no change (204), still proceed to send replies
                if ack.get("type") == "ack" and ack.get("ok") and ack.get("code") in (200, 204):
                    # Send configured number of replies after each update
                    for _ in range(PERSONALITY_REPLIES_PER_SWITCH):
                        user_text = PERSONA_SWITCH_REPLIES[reply_idx % len(PERSONA_SWITCH_REPLIES)]
                        reply_idx += 1
                        final_text = await send_start(ws, session_id, g, p, c, TOOLCALL_PROMPT, history_text, user_text)
                        history_text = (history_text + f"\nUser: {user_text}\nAssistant: {final_text}").strip()
                else:
                    raise RuntimeError(f"update_chat_prompt failed: {ack}")
        finally:
            await send_client_end(ws)


def main() -> None:
    parser = argparse.ArgumentParser(description="Personality switch WS test")
    parser.add_argument(
        "--ws",
        dest="ws",
        default=DEFAULT_SERVER_WS_URL,
        help=f"WebSocket URL (default: {DEFAULT_SERVER_WS_URL})",
    )
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

    switches = max(PERSONALITY_SWITCH_MIN, min(PERSONALITY_SWITCH_MAX, args.switches))
    asyncio.run(run_test(args.ws, switches, args.delay))


if __name__ == "__main__":
    main()


