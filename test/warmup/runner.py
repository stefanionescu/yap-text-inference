from __future__ import annotations

import asyncio
import json
import os
import uuid
import time
import websockets
from typing import Any, Dict

from common.regex import contains_complete_sentence, has_at_least_n_words
from common.ws import with_api_key
from .messages import choose_message


async def run_once(args) -> None:
    server_ws_url = os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws")
    api_key = os.getenv("TEXT_API_KEY", "yap_token")
    assistant_gender = args.assistant_gender or os.getenv("ASSISTANT_GENDER", "female")
    persona_style = args.persona_style or os.getenv("PERSONA_STYLE", "flirty")

    ws_url_with_auth = with_api_key(server_ws_url)

    user_msg = choose_message(args.message)
    session_id = str(uuid.uuid4())
    start_payload: Dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "assistant_gender": assistant_gender,
        "persona_style": persona_style,
        "history_text": "",
        "user_utterance": user_msg,
    }

    print(f"Connecting to {server_ws_url} (with API key auth) …")
    async with websockets.connect(ws_url_with_auth, max_queue=None) as ws:
        await ws.send(json.dumps(start_payload))

        final_text = ""
        ack_seen = False
        recv_timeout = float(os.getenv("RECV_TIMEOUT_SEC", "60"))
        first_token_ts: float | None = None
        first_sentence_ts: float | None = None
        first_3_words_ts: float | None = None
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
                now = msg.get("now")
                gender = msg.get("assistant_gender")
                style = msg.get("persona_style")
                models = msg.get("models", {})
                print(f"ACK start → now='{now}' gender={gender} style={style} models={models}")
                continue

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
                if first_3_words_ts is None and has_at_least_n_words(final_text, 3):
                    first_3_words_ts = time.perf_counter()
                    first_3_words_ms = (first_3_words_ts - sent_ts) * 1000.0
                    print(f"CHAT time_to_first_3_words_ms={round(first_3_words_ms, 2)}")
                if first_sentence_ts is None and contains_complete_sentence(final_text):
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
                    "time_to_first_3_words_ms": round((first_3_words_ts - sent_ts) * 1000.0, 2) if first_3_words_ts is not None else None,
                    "chunks": chunks,
                    "chars": len(final_text),
                }, ensure_ascii=False))
                print(json.dumps({
                    "type": "final_text",
                    "text": final_text,
                }, ensure_ascii=False))
                break

            if t == "error":
                error_code = msg.get("error_code", "")
                error_message = msg.get("message", "unknown error")
                print(f"[ERROR] {error_code}: {error_message}")
                if error_code == "authentication_failed":
                    print(f"[HINT] Check your TEXT_API_KEY environment variable (currently: '{api_key}')")
                elif error_code == "server_at_capacity":
                    print("[HINT] Server is at maximum connection capacity. Try again later.")
                break

        if not ack_seen:
            print("[WARN] no ACK(start) received from server")


