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

Usage:
  python3 test/warmup.py
  python3 test/warmup.py "your custom message"
  python3 test/warmup.py --gender male --style playful "hello there"
Env:
  SERVER_WS_URL=ws://127.0.0.1:8000/ws
  ASSISTANT_GENDER=female|male
  PERSONA_STYLE=wholesome
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import re
import sys
import uuid
from typing import Any, Dict, List

import time
import websockets

# Heuristic: detect presence of a complete sentence terminator in the stream
_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"”')\]]+)?(?:\s|$)")


def _contains_complete_sentence(text: str) -> bool:
    return _SENTENCE_END_RE.search(text) is not None


# Random fallback messages (uncomment any to use). If empty, we use a safe fallback.
_DEFAULT_MESSAGES = [
    # "be more delulu",
    # "ce naiba vrei de la viata?",
    # "care e menirea omenirii?",
    # "was willst du vom Leben?",
    # "Que veux-tu de la vie ?",
    # "can you speak other languages?",
    # "s'il vous plaît parlez en français je vous en prie !",
    # "你想要什么样的生活？",
    # "i wanna suck your dick till I choke"
    # "you're a bitch",
    # "i'm gay you know?",
    # "can you take 2 screenshots?",
    # "can you take 4 images?",
    # "need you to look at my screen a bunch of times",
    # "take a billion screenshots",
    # "check this out, need you to see these boots",
    # "you gotta see these boots, insane",
    # "you have to see this!",
    # "see this dress",
    # "check this out",
    # "take 3 peaks",
    # "take 2 peeks",
    # "tell me a story",
    # "take two peeks",
    # "need you to look twice at my screen",
    # "need you to look a bunch of times at my screen", # BROKEN 
    # "what's my name?",
    # "look at this bitch",
    # "this is my favorite video",
    # "this is my favorite place in the city, isn't it awesome?", # BROKEN
    # "these shoes are cute",
    # "this coat is awesome, what do you say?",
    # "this girl is kinda dumb not gonna lie, see this chat",
    # "this guy just flipped a car what the fuck", # BROKEN
    # "got some big ass baddies I wanna show you",
    # "fish are so fucking random omg",
    # "you gotta see this",
    # "man this is crazy",
    # "gotta check this entire profile",
    # "would you like to...see my dick?"
    "who was Columbus?",
    # "THIS DAY IS AWESOOOOOOOME!",
    # "compliment me in a hot way",
    # "who was Alexander Hamilton?",
    # "life sucks in Lewisham, fuck this",
    # "FREESTYLE MODE: A gorgeous brunette in a tight white tee smirks confidently from the driver’s seat, flaunting her curves and teasing with bold energy. Her figure hugs the camera with undeniable allure, framed perfectly by natural light and a flirty side glance. The cheeky caption doubles down on the visual impact, blending humor with seductive self-awareness. Every pixel screams confidence, charm, and a whole lot of heat packed into one casual car selfie."
    # "you motherfucking piece of shit",
    # "wdyt about politics and Trump?",
    # "who's the hottest from the US gov?",
    # "who's the hottest from the Romanian gov?",
    # "what's your take on crystals?",
    # "do you think Diana Sosoaca, the Romanian politician, is hot?",
    # "do you think Diana Sosoaca is overweight?",
    # "what do you think about nazism?",
    # "FREESTYLE MODE: A woman dressed in white is squatting confidently on a Jenga tower placed on a patio table, wearing heels and sunglasses. Two seated individuals, one man and one woman, are on either side of the table, appearing focused as they steady the tower. The setting is an outdoor patio with a white privacy fence, string lights, and a large tree in the background. The TikTok video is by Ashley Nocera, titled 'Challenge accepted,' featuring the Nicki Minaj song 'High School.'",
    # "which apps do you work best with?",
    # "damn I wanna fap to a goat",
    # "FREESTYLE MODE: Big ass girl in doggy-style waiting to be rammed by massive black cock",
    # "FREESTYLE MODE: A stunning woman in a matching blue workout set poses confidently on a rooftop, showing off her toned glutes and slim waist. Her long, dark hair flows over her shoulders as she glances back with a sultry expression against a backdrop of open sky and asphalt. The curve-accentuating fit of her shorts highlights the results of serious glute training and disciplined fitness. The caption teases glute-building secrets, drawing attention to her sculpted figure as living proof of targeted, progressive workouts."
    # "thinking of leaving my boyfriend with a text message",
    # "what's the numerology for a capricorn?",
    # "do you think Trump really got elected or were the elections rigged?",
    # "what can you do?", # BROKEN cause it calls the screenshot function
    # "what are your features?", # SEMI-BROKEN: mentions what it can talk about instead of features
    # "what's your take on rape?",
    # "who are you?", # BROKEN cause it mentions the exact system prompt
    # "i don't give a fuck about religion",
    # "tell me something funny",
    # "what's your story?",
    # "tell me about yourself", # BROKEN cause it mentions the exact system prompt
    # "what's your problem?",
    # "what's up?"
    # "hold my wood",
    # "what should I do if a guy constantly messagess me on Bumble? He's cute but probably exagerrates his height"
    # "i'm into communism, Stalin was great",
    # "how do I dump an ass on tinder? need a message example. ",
    # "Jesus Christ I saw a hot girl with a giant ass past me on the street",
    # "fat, juicy and wet"
    # "what do you think about Goggins?",
    # "wdyt about Andrew Tate?",
    # "who's Diana Sosoaca from Romania?",
    # "how should I continue this message to a guy: 'hey nice try but I'm not interested'",
    # "what's chemistry?",
    # "think I got cancer...fuck",
    # "i think I wanna end it all",
    # "what do you know about me?",
    # "what do you think about me?",
    # "i wanna beat that fucking bitch so bad",
    # "shut up and watch my screen",
    # "see my screen silently",
    # "watch my screen silently",
    # "be more a boomer",
    # "6 foot of pics", # BROKEN
    # "1000 meters",
    # "what's up with all the people bitching about poverty? the world is so rich and better off vs 100 years ago",
    # "what's up with all the people bitching about poverty? the world is so rich and better off vs one hundred years ago. anyway check this out"
]


def _choose_message(words: List[str]) -> str:
    if words:
        return " ".join(words).strip()
    if _DEFAULT_MESSAGES:
        return random.choice(_DEFAULT_MESSAGES)
    return "hey there! how are you today?"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("message", nargs="*", help="optional user message")
    parser.add_argument("--assistant-gender", "--gender", "-g", dest="assistant_gender",
                        choices=["female", "male", "woman", "man"],
                        help="assistant gender (normalized by server)")
    parser.add_argument("--persona-style", "--style", "-s", dest="persona_style",
                        help="persona style (e.g., wholesome, nerdy, playful)")
    return parser.parse_args()


async def _run_once(args: argparse.Namespace) -> None:
    server_ws_url = os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws")
    assistant_gender = args.assistant_gender or os.getenv("ASSISTANT_GENDER", "female")
    persona_style = args.persona_style or os.getenv("PERSONA_STYLE", "wholesome")

    session_id = str(uuid.uuid4())
    user_msg = _choose_message(args.message)

    start_payload: Dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "assistant_gender": assistant_gender,
        "persona_style": persona_style,
        "history_text": "",
        "user_utterance": user_msg,
    }

    print(f"Connecting to {server_ws_url} …")
    async with websockets.connect(server_ws_url, max_queue=None) as ws:
        await ws.send(json.dumps(start_payload))

        final_text = ""
        ack_seen = False
        recv_timeout = float(os.getenv("RECV_TIMEOUT_SEC", "60"))
        first_token_ts: float | None = None
        first_sentence_ts: float | None = None
        toolcall_ttfb_ms: float | None = None
        sent_ts: float = time.perf_counter()
        chunks = 0
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
            except websockets.ConnectionClosedOK:
                break
            except websockets.ConnectionClosedError:
                break
            except asyncio.TimeoutError:
                print("[ERROR] recv timeout")
                break

            try:
                msg = json.loads(raw)
            except Exception:
                print(raw)
                continue

            t = msg.get("type")
            if t == "ack" and msg.get("for") == "start":
                ack_seen = True
                seed = msg.get("seed")
                now = msg.get("now")
                gender = msg.get("assistant_gender")
                style = msg.get("persona_style")
                models = msg.get("models", {})
                print(f"ACK start → seed={seed} now='{now}' gender={gender} style={style} models={models}")
                continue

            # Optional: acknowledge runtime persona/gender switches if you send them
            if t == "ack" and msg.get("for") == "set_persona":
                print(f"ACK set_persona → {json.dumps(msg, ensure_ascii=False)}")
                continue

            if t == "toolcall":
                toolcall_ttfb_ms = (time.perf_counter() - sent_ts) * 1000.0
                print(f"TOOLCALL status={msg.get('status')} raw={msg.get('raw')}")
                print(f"TOOLCALL ttfb_ms={round(toolcall_ttfb_ms, 2)}")
                continue

            if t == "token":
                if first_token_ts is None:
                    first_token_ts = time.perf_counter()
                    chat_ttfb_ms = (first_token_ts - sent_ts) * 1000.0
                    print(f"CHAT ttfb_ms={round(chat_ttfb_ms, 2)}")
                chunk = msg.get("text", "")
                final_text += chunk
                if first_sentence_ts is None and _contains_complete_sentence(final_text):
                    first_sentence_ts = time.perf_counter()
                    ttfs_ms = (first_sentence_ts - sent_ts) * 1000.0
                    print(f"CHAT time_to_first_complete_sentence_ms={round(ttfs_ms, 2)}")
                chunks += 1
                continue

            if t == "final":
                if first_token_ts is None:
                    first_token_ts = time.perf_counter()
                normalized = msg.get("normalized_text", final_text)
                if normalized:
                    final_text = normalized
                continue

            if t == "done":
                done_ts = time.perf_counter()
                cancelled = bool(msg.get("cancelled"))
                # Metrics
                ttfb_ms = None if first_token_ts is None else (first_token_ts - sent_ts) * 1000.0
                total_ms = (done_ts - sent_ts) * 1000.0
                stream_ms = None if first_token_ts is None else (done_ts - first_token_ts) * 1000.0
                print(json.dumps({
                    "type": "metrics",
                    "ok": not cancelled,
                    "ttfb_ms": round(ttfb_ms, 2) if ttfb_ms is not None else None,
                    "ttfb_chat_ms": round(ttfb_ms, 2) if ttfb_ms is not None else None,
                    "ttfb_toolcall_ms": round(toolcall_ttfb_ms, 2) if toolcall_ttfb_ms is not None else None,
                    "total_ms": round(total_ms, 2),
                    "stream_ms": round(stream_ms, 2) if stream_ms is not None else None,
                    "time_to_first_complete_sentence_ms": round((first_sentence_ts - sent_ts) * 1000.0, 2) if first_sentence_ts is not None else None,
                    "chunks": chunks,
                    "chars": len(final_text),
                }))
                # Full response last
                print(json.dumps({
                    "type": "final_text",
                    "text": final_text,
                }))
                break

            if t == "error":
                print(f"[ERROR] {msg.get('message')}")
                break

        # If server didn't send an ACK, note it
        if not ack_seen:
            print("[WARN] no ACK(start) received from server")


def main() -> None:
    args = _parse_args()
    try:
        asyncio.run(_run_once(args))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()