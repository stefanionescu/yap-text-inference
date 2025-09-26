#!/usr/bin/env python3
"""
Concurrent benchmark for the WebSocket /ws endpoint.

Runs N total sessions with up to M concurrent connections. For each request,
records:
- ttfb_toolcall_ms: time to receive toolcall decision
- ttfb_chat_ms: time to first chat token (if chat happens)
- first_sentence_ms: time to first complete sentence (if chat happens)
- first_3_words_ms: time to first three words (if chat happens)

Prints p50/p95 for each metric across completed requests. No intermediate logs.

Environment Variables:
- SERVER_WS_URL: WebSocket URL (default: ws://127.0.0.1:8000/ws)
- YAP_API_KEY: API key for authentication (default: yap_token)
- ASSISTANT_GENDER: female|male (default: female)
- PERSONA_STYLE: persona style (default: flirty)

Note: API key authentication is required. The client will automatically
append the API key as a query parameter to all WebSocket connections.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import websockets


_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"”')\]]+)?(?:\s|$)")


def _contains_complete_sentence(text: str) -> bool:
    return _SENTENCE_END_RE.search(text) is not None


def _has_at_least_n_words(text: str, n: int) -> bool:
    # Whitespace-delimited token count; counts punctuation-attached tokens as words
    return len(text.strip().split()) >= n


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Benchmark Yap Text Inference WS server")
    p.add_argument("message", nargs="*", help="optional user message for all requests")
    p.add_argument("--requests", "-n", type=int, default=16, help="total number of requests")
    p.add_argument("--concurrency", "-c", type=int, default=8, help="max in-flight requests")
    p.add_argument("--timeout", type=float, default=120.0, help="per-request total timeout (s)")
    p.add_argument(
        "--url",
        default=os.getenv("SERVER_WS_URL", "ws://127.0.0.1:8000/ws"),
        help="WebSocket URL (default env SERVER_WS_URL or ws://127.0.0.1:8000/ws)",
    )
    p.add_argument(
        "--assistant-gender",
        "--gender",
        "-g",
        dest="assistant_gender",
        choices=["female", "male", "woman", "man"],
        default=os.getenv("ASSISTANT_GENDER", "female"),
        help="assistant gender (normalized by server)",
    )
    p.add_argument(
        "--persona-style",
        "--style",
        "-s",
        dest="persona_style",
        default=os.getenv("PERSONA_STYLE", "flirty"),
        help="persona style (e.g., wholesome, nerdy, flirty)",
    )
    return p.parse_args()


def _choose_message(words: List[str]) -> str:
    if words:
        return " ".join(words).strip()
    return "who was Columbus?"


async def _one_request(url: str, gender: str, style: str, message: str, timeout_s: float) -> Dict[str, Any]:
    async def _session() -> Dict[str, Any]:
        # Add API key authentication to the URL
        api_key = os.getenv("YAP_API_KEY", "yap_token")
        if "?" in url:
            auth_url = f"{url}&api_key={api_key}"
        else:
            auth_url = f"{url}?api_key={api_key}"
        
        session_id = str(uuid.uuid4())
        start_payload: Dict[str, Any] = {
            "type": "start",
            "session_id": session_id,
            "assistant_gender": gender,
            "persona_style": style,
            "history_text": "",
            "user_utterance": message,
        }

        t_sent = time.perf_counter()
        ttfb_toolcall_ms: Optional[float] = None
        ttfb_chat_ms: Optional[float] = None
        first_sentence_ms: Optional[float] = None
        first_3_words_ms: Optional[float] = None
        final_text = ""

        async with websockets.connect(auth_url, max_queue=None) as ws:
            await ws.send(json.dumps(start_payload))

            while True:
                raw = await ws.recv()
                try:
                    msg = json.loads(raw)
                except Exception:
                    continue
                t = msg.get("type")

                if t == "toolcall":
                    if ttfb_toolcall_ms is None:
                        ttfb_toolcall_ms = (time.perf_counter() - t_sent) * 1000.0
                    continue

                if t == "token":
                    if ttfb_chat_ms is None:
                        ttfb_chat_ms = (time.perf_counter() - t_sent) * 1000.0
                    chunk = msg.get("text", "")
                    final_text += chunk
                    if first_3_words_ms is None and _has_at_least_n_words(final_text, 3):
                        first_3_words_ms = (time.perf_counter() - t_sent) * 1000.0
                    if first_sentence_ms is None and _contains_complete_sentence(final_text):
                        first_sentence_ms = (time.perf_counter() - t_sent) * 1000.0
                    continue

                if t == "final":
                    normalized = msg.get("normalized_text")
                    if normalized:
                        final_text = normalized
                    continue

                if t == "done":
                    cancelled = bool(msg.get("cancelled"))
                    return {
                        "ok": not cancelled,
                        "ttfb_toolcall_ms": ttfb_toolcall_ms,
                        "ttfb_chat_ms": ttfb_chat_ms,
                        "first_sentence_ms": first_sentence_ms,
                        "first_3_words_ms": first_3_words_ms,
                    }

                if t == "error":
                    error_code = msg.get("error_code", "")
                    error_message = msg.get("message", "unknown error")
                    # Include error code for better debugging
                    return {"ok": False, "error": f"{error_code}: {error_message}" if error_code else error_message}

    try:
        return await asyncio.wait_for(_session(), timeout=timeout_s)
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _worker(num: int, url: str, gender: str, style: str, message: str, timeout_s: float) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for _ in range(num):
        out.append(await _one_request(url, gender, style, message, timeout_s))
    return out


def _pct(values: List[float], frac: float, minus_one: bool = False) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    n = len(vals)
    idx = int(frac * n)
    if minus_one:
        idx = max(idx - 1, 0)
    if idx >= n:
        idx = n - 1
    return vals[idx]


async def _main_async(args: argparse.Namespace) -> None:
    url: str = args.url
    gender: str = args.assistant_gender
    style: str = args.persona_style
    message: str = _choose_message(args.message)

    requests = max(1, int(args.requests))
    concurrency = max(1, min(int(args.concurrency), requests))
    base, rem = divmod(requests, concurrency)
    counts = [base + (1 if i < rem else 0) for i in range(concurrency)]

    tasks = [
        asyncio.create_task(_worker(counts[i], url, gender, style, message, float(args.timeout)))
        for i in range(concurrency)
        if counts[i] > 0
    ]
    nested = await asyncio.gather(*tasks)
    results: List[Dict[str, Any]] = [item for sub in nested for item in sub]

    ok = [r for r in results if r.get("ok")]
    errs = [r for r in results if not r.get("ok")]
    tool_ttfb = [r["ttfb_toolcall_ms"] for r in ok if r.get("ttfb_toolcall_ms") is not None]
    chat_ttfb = [r["ttfb_chat_ms"] for r in ok if r.get("ttfb_chat_ms") is not None]
    first_sentence = [r["first_sentence_ms"] for r in ok if r.get("first_sentence_ms") is not None]
    first_3_words = [r["first_3_words_ms"] for r in ok if r.get("first_3_words_ms") is not None]

    print(
        f"url={url} total={requests} conc={concurrency} ok={len(ok)} err={len(errs)}"
    )
    if tool_ttfb:
        p50 = _pct(tool_ttfb, 0.5)
        p95 = _pct(tool_ttfb, 0.95, minus_one=True)
        print(f"toolcall_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if chat_ttfb:
        p50 = _pct(chat_ttfb, 0.5)
        p95 = _pct(chat_ttfb, 0.95, minus_one=True)
        print(f"chat_ttfb_ms p50={p50:.1f} p95={p95:.1f}")
    if first_sentence:
        p50 = _pct(first_sentence, 0.5)
        p95 = _pct(first_sentence, 0.95, minus_one=True)
        print(f"first_sentence_ms p50={p50:.1f} p95={p95:.1f}")
    if first_3_words:
        p50 = _pct(first_3_words, 0.5)
        p95 = _pct(first_3_words, 0.95, minus_one=True)
        print(f"first_3_words_ms p50={p50:.1f} p95={p95:.1f}")

    # Optional: show one error example for debugging
    if errs:
        e = errs[0]
        emsg = e.get("error", "unknown error")
        print(f"example_error={emsg}")
        
        # Special hints for common authentication issues
        if "authentication_failed" in emsg:
            api_key = os.getenv("YAP_API_KEY", "yap_token")
            print(f"hint: Check YAP_API_KEY environment variable (currently: '{api_key}')")
        elif "server_at_capacity" in emsg:
            print("hint: Server at capacity. Reduce concurrency (-c) or try again later.")


def main() -> None:
    args = _parse_args()
    asyncio.run(_main_async(args))


if __name__ == "__main__":
    main()


