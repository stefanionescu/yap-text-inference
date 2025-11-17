import asyncio
import json
import os
import uuid
import argparse
from typing import List, Tuple

import websockets

from test.prompts.chat import FIRST_PROMPT, SECOND_PROMPT
from test.prompts.toolcall import TOOLCALL_PROMPT


MOCK_REPLIES: List[str] = [
    "Hey there, how are you?",
    "What are you up to right now?",
    "Tell me something interesting about yourself.",
    "Do you prefer mornings or nights?",
    "What's your current vibe?",
    "Give me your take on this week.",
    "What would you do on a free day?",
    "Are you more spontaneous or a planner?",
    "What's a hot take you stand by?",
    "What annoys you the most?",
    "What do you think about road trips?",
    "What's your idea of fun?",
    "What was the last thing that made you laugh?",
    "What topic do you always have an opinion on?",
    "What's overrated right now?",
    "What's underrated right now?",
    "Describe your perfect evening in 5 words.",
    "What's your favorite guilty pleasure?",
    "What's something you refuse to do?",
    "What's your dream weekend like?",
]


def get_api_key() -> str:
    return os.getenv("TEXT_API_KEY", "")


def build_ws_url(base: str, api_key: str) -> str:
    if not api_key:
        return base
    sep = '&' if ('?' in base) else '?'
    return f"{base}{sep}api_key={api_key}"


async def recv_until_done(ws) -> Tuple[str, List[dict]]:
    tokens = []
    final_text = ""
    toolcalls: List[dict] = []
    while True:
        msg = json.loads(await ws.receive()) if hasattr(ws, 'receive') else json.loads(await ws.recv())
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
        "type": "update_chat_prompt",
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
        if ack.get("type") == "ack" and ack.get("for") == "update_chat_prompt":
            return ack
        if ack.get("type") == "error":
            return ack


async def run_test(ws_url: str, switches: int, delay_s: int) -> None:
    api_key = get_api_key()
    url = build_ws_url(ws_url, api_key)
    session_id = f"sess-{uuid.uuid4()}"

    # Cycle between two prompts/genders/personalities
    variants = [
        ("female", "anna", FIRST_PROMPT),
        ("male", "mark", SECOND_PROMPT),
    ]

    history_text = ""
    reply_idx = 0

    async with websockets.connect(url, ping_interval=20, ping_timeout=20) as ws:
        # Initial start with first variant and a simple opener
        g0, p0, c0 = variants[0]
        opener = MOCK_REPLIES[reply_idx % len(MOCK_REPLIES)]
        reply_idx += 1
        final0 = await send_start(ws, session_id, g0, p0, c0, TOOLCALL_PROMPT, history_text, opener)
        history_text = f"User: {opener}\nAssistant: {final0}".strip()

        for i in range(switches):
            await asyncio.sleep(delay_s)
            g, p, c = variants[(i + 1) % len(variants)]

            ack = await send_update_chat_prompt(ws, session_id, g, p, c, history_text)
            # If no change (204), still proceed to send replies
            if ack.get("type") == "ack" and ack.get("ok") and ack.get("code") in (200, 204):
                # Send two replies after each update
                for _ in range(2):
                    user_text = MOCK_REPLIES[reply_idx % len(MOCK_REPLIES)]
                    reply_idx += 1
                    final_text = await send_start(ws, session_id, g, p, c, TOOLCALL_PROMPT, history_text, user_text)
                    history_text = (history_text + f"\nUser: {user_text}\nAssistant: {final_text}").strip()
            else:
                raise RuntimeError(f"update_chat_prompt failed: {ack}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Personality switch WS test")
    parser.add_argument("--ws", dest="ws", default="ws://localhost:8000/ws", help="WebSocket URL (default: ws://localhost:8000/ws)")
    parser.add_argument("--switches", dest="switches", type=int, default=4, help="Number of chat prompt switches (1-10), default 4")
    parser.add_argument("--delay", dest="delay", type=int, default=10, help="Seconds between switches (default 10)")
    args = parser.parse_args()

    switches = max(1, min(10, args.switches))
    asyncio.run(run_test(args.ws, switches, args.delay))


if __name__ == "__main__":
    main()


