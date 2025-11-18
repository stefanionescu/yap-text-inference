from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from typing import Any

import websockets

from common.message import iter_messages
from common.prompt import select_chat_prompt
from common.regex import contains_complete_sentence, has_at_least_n_words
from common.util import choose_message
from common.ws import send_client_end, with_api_key
from .reporting import print_report

# Ensure prompts/config modules are importable when running as script
_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from config import BENCHMARK_FALLBACK_MESSAGE  # noqa: E402
from prompts.toolcall import TOOLCALL_PROMPT  # noqa: E402


async def _one_request(url: str, gender: str, style: str, message: str, timeout_s: float) -> dict[str, Any]:
    async def _session() -> dict[str, Any]:
        auth_url = with_api_key(url)

        session_id = str(uuid.uuid4())
        chat_prompt = select_chat_prompt(gender)
        start_payload: dict[str, Any] = {
            "type": "start",
            "session_id": session_id,
            "gender": gender,
            "personality": style,
            "chat_prompt": chat_prompt,
            "tool_prompt": TOOLCALL_PROMPT,
            "history_text": "",
            "user_utterance": message,
        }

        t_sent = time.perf_counter()
        ttfb_toolcall_ms: float | None = None
        ttfb_chat_ms: float | None = None
        first_sentence_ms: float | None = None
        first_3_words_ms: float | None = None
        final_text = ""

        async with websockets.connect(auth_url, max_queue=None) as ws:
            try:
                await ws.send(json.dumps(start_payload))

                async for msg in iter_messages(ws):
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
                        if first_3_words_ms is None and has_at_least_n_words(final_text, 3):
                            first_3_words_ms = (time.perf_counter() - t_sent) * 1000.0
                        if first_sentence_ms is None and contains_complete_sentence(final_text):
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
                        return {"ok": False, "error": f"{error_code}: {error_message}" if error_code else error_message}
            finally:
                await send_client_end(ws)

    try:
        return await asyncio.wait_for(_session(), timeout=timeout_s)
    except Exception as e:
        return {"ok": False, "error": str(e)}


async def _worker(num: int, url: str, gender: str, style: str, message: str, timeout_s: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for _ in range(num):
        out.append(await _one_request(url, gender, style, message, timeout_s))
    return out


async def run_benchmark(args) -> None:
    url: str = args.url
    gender: str = args.gender
    style: str = args.personality
    message: str = choose_message(args.message, fallback=BENCHMARK_FALLBACK_MESSAGE)

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
    results: list[dict[str, Any]] = [item for sub in nested for item in sub]

    print_report(url, requests, concurrency, results)


