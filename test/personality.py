import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from collections.abc import Sequence

import websockets

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from test.common.message import iter_messages
from test.common.rate import SlidingWindowPacer
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
from test.config.env import get_float_env, get_int_env
from test.prompts.toolcall import TOOLCALL_PROMPT


PERSONA_WINDOW_SECONDS = get_float_env("CHAT_PROMPT_UPDATE_WINDOW_SECONDS", 60.0)
PERSONA_MAX_PER_WINDOW = get_int_env("CHAT_PROMPT_UPDATE_MAX_PER_WINDOW", 4)
MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


@dataclass(frozen=True)
class PersonaVariant:
    gender: str
    personality: str
    chat_prompt: str


@dataclass
class PersonaSession:
    session_id: str
    history: str = ""
    reply_index: int = 0
    replies: Sequence[str] = field(default_factory=lambda: PERSONA_SWITCH_REPLIES)

    def next_user_prompt(self) -> str:
        if not self.replies:
            raise RuntimeError("PERSONA_SWITCH_REPLIES is empty; cannot produce user prompts.")
        prompt = self.replies[self.reply_index % len(self.replies)]
        self.reply_index += 1
        return prompt

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()


async def _collect_response(ws) -> str:
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
            return final_text
        if t == "error":
            raise RuntimeError(f"server error: {msg}")
    raise RuntimeError("WebSocket closed before receiving 'done'")


async def _send_start_request(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    user_text: str,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> str:
    payload = {
        "type": "start",
        "session_id": session.session_id,
        "gender": variant.gender,
        "personality": variant.personality,
        "chat_prompt": variant.chat_prompt,
        "tool_prompt": TOOLCALL_PROMPT,
        "history_text": session.history,
        "user_utterance": user_text,
    }
    if message_pacer:
        await message_pacer.wait_turn()
    await ws.send(json.dumps(payload))
    reply = await _collect_response(ws)
    print(
        f"[persona={variant.personality} gender={variant.gender}] "
        f"user: {user_text!r} -> assistant: {reply!r}"
    )
    return reply


async def _wait_for_chat_prompt_ack(ws) -> dict:
    async for msg in iter_messages(ws):
        if msg.get("type") == "ack" and msg.get("for") == "chat_prompt":
            return msg
        if msg.get("type") == "error":
            return msg
    raise RuntimeError("WebSocket closed before receiving chat_prompt ack")


async def _send_persona_update(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    persona_pacer: SlidingWindowPacer | None = None,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    payload = {
        "type": "chat_prompt",
        "session_id": session.session_id,
        "gender": variant.gender,
        "personality": variant.personality,
        "chat_prompt": variant.chat_prompt,
        "history_text": session.history,
    }
    if persona_pacer:
        await persona_pacer.wait_turn()
    if message_pacer:
        await message_pacer.wait_turn()
    await ws.send(json.dumps(payload))
    ack = await _wait_for_chat_prompt_ack(ws)
    if not (ack.get("type") == "ack" and ack.get("ok") and ack.get("code") in (200, 204)):
        raise RuntimeError(f"update_chat_prompt failed: {ack}")


async def _run_initial_exchange(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    opener = session.next_user_prompt()
    assistant_text = await _send_start_request(
        ws,
        session,
        variant,
        opener,
        message_pacer=message_pacer,
    )
    session.append_exchange(opener, assistant_text)


async def _run_switch_sequence(
    ws,
    session: PersonaSession,
    variant: PersonaVariant,
    *,
    persona_pacer: SlidingWindowPacer | None = None,
    message_pacer: SlidingWindowPacer | None = None,
) -> None:
    await _send_persona_update(
        ws,
        session,
        variant,
        persona_pacer=persona_pacer,
        message_pacer=message_pacer,
    )
    for _ in range(PERSONALITY_REPLIES_PER_SWITCH):
        user_text = session.next_user_prompt()
        assistant_text = await _send_start_request(
            ws,
            session,
            variant,
            user_text,
            message_pacer=message_pacer,
        )
        session.append_exchange(user_text, assistant_text)


async def run_test(ws_url: str, switches: int, delay_s: int) -> None:
    url = with_api_key(ws_url)
    session = PersonaSession(session_id=f"sess-{uuid.uuid4()}")
    variants: list[PersonaVariant] = [PersonaVariant(*variant) for variant in PERSONA_VARIANTS]
    if not variants:
        raise RuntimeError("PERSONA_VARIANTS is empty; nothing to test.")

    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)
    persona_pacer = SlidingWindowPacer(PERSONA_MAX_PER_WINDOW, PERSONA_WINDOW_SECONDS)

    async with websockets.connect(
        url,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            await _run_initial_exchange(
                ws,
                session,
                variants[0],
                message_pacer=message_pacer,
            )
            for i in range(switches):
                await asyncio.sleep(delay_s)
                variant = variants[(i + 1) % len(variants)]
                await _run_switch_sequence(
                    ws,
                    session,
                    variant,
                    persona_pacer=persona_pacer,
                    message_pacer=message_pacer,
                )
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


