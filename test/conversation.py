#!/usr/bin/env python3
"""
Conversation history tester.

Opens a websocket session, reuses a single persona, and replays a scripted
ten-turn conversation to verify that history retention and KV-cache behavior
remain stable under bounded-history constraints. Each exchange logs:
  - user + assistant text
  - time to first token (TTFB)
  - time to first three words
  - time to first complete sentence

Usage:
    python3 test/conversation.py
    python3 test/conversation.py --server ws://127.0.0.1:8000/ws
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Sequence

import websockets  # type: ignore[import-not-found]

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from test.common.cli import add_connection_args
from test.common.message import iter_messages
from test.common.prompt import select_chat_prompt
from test.common.rate import SlidingWindowPacer
from test.common.regex import contains_complete_sentence, has_at_least_n_words
from test.common.ws import send_client_end, with_api_key
from test.config import (
    CONVERSATION_HISTORY_PROMPTS,
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from test.config.env import get_float_env, get_int_env
from test.prompts.toolcall import TOOLCALL_PROMPT

logger = logging.getLogger(__name__)


MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conversation history regression test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    parser.add_argument(
        "--gender",
        dest="gender",
        help="Assistant gender override (defaults to env/DEFAULT_GENDER)",
    )
    parser.add_argument(
        "--personality",
        dest="personality",
        help="Assistant personality override (defaults to env/DEFAULT_PERSONALITY)",
    )
    parser.add_argument(
        "--recv-timeout",
        dest="recv_timeout",
        type=float,
        default=DEFAULT_RECV_TIMEOUT_SEC,
        help=f"Receive timeout in seconds (default: {DEFAULT_RECV_TIMEOUT_SEC})",
    )
    return parser.parse_args()


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


@dataclass
class StreamTracker:
    sent_ts: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    ack_seen: bool = False
    first_token_ts: float | None = None
    first_sentence_ts: float | None = None
    first_3_words_ts: float | None = None
    toolcall_ttfb_ms: float | None = None
    chunks: int = 0

    def _ms_since_sent(self, timestamp: float | None) -> float | None:
        if timestamp is None:
            return None
        return (timestamp - self.sent_ts) * 1000.0

    def record_toolcall(self) -> float | None:
        now = time.perf_counter()
        self.toolcall_ttfb_ms = self._ms_since_sent(now)
        return self.toolcall_ttfb_ms

    def record_token(self, chunk: str) -> dict[str, float | None]:
        metrics: dict[str, float | None] = {}
        if not chunk:
            return metrics

        if self.first_token_ts is None:
            self.first_token_ts = time.perf_counter()
            metrics["chat_ttfb_ms"] = self._ms_since_sent(self.first_token_ts)

        self.final_text += chunk
        if self.first_3_words_ts is None and has_at_least_n_words(self.final_text, 3):
            self.first_3_words_ts = time.perf_counter()
            metrics["time_to_first_3_words_ms"] = self._ms_since_sent(self.first_3_words_ts)

        if self.first_sentence_ts is None and contains_complete_sentence(self.final_text):
            self.first_sentence_ts = time.perf_counter()
            metrics["time_to_first_complete_sentence_ms"] = self._ms_since_sent(self.first_sentence_ts)

        self.chunks += 1
        return metrics

    def finalize_metrics(self, cancelled: bool) -> dict[str, Any]:
        done_ts = time.perf_counter()
        ttfb_ms = self._ms_since_sent(self.first_token_ts)
        stream_ms = None
        if self.first_token_ts is not None:
            stream_ms = (done_ts - self.first_token_ts) * 1000.0
        total_ms = (done_ts - self.sent_ts) * 1000.0
        return {
            "ok": not cancelled,
            "ttfb_ms": _round(ttfb_ms),
            "ttfb_chat_ms": _round(ttfb_ms),
            "ttfb_toolcall_ms": _round(self.toolcall_ttfb_ms),
            "total_ms": _round(total_ms),
            "stream_ms": _round(stream_ms),
            "time_to_first_complete_sentence_ms": _round(self._ms_since_sent(self.first_sentence_ts)),
            "time_to_first_3_words_ms": _round(self._ms_since_sent(self.first_3_words_ts)),
            "chunks": self.chunks,
            "chars": len(self.final_text),
        }


@dataclass
class ConversationSession:
    session_id: str
    gender: str
    personality: str
    chat_prompt: str
    history: str = ""

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()


def _build_start_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    return {
        "type": "start",
        "session_id": session.session_id,
        "gender": session.gender,
        "personality": session.personality,
        "chat_prompt": session.chat_prompt,
        "history_text": session.history,
        "user_utterance": user_text,
        "tool_prompt": TOOLCALL_PROMPT,
    }


async def _stream_exchange(ws, tracker: StreamTracker, recv_timeout: float, exchange_idx: int) -> str:
    async for msg in iter_messages(ws, timeout=recv_timeout):
        msg_type = msg.get("type")
        if msg_type == "ack":
            tracker.ack_seen = True
            logger.info(
                "Exchange %02d ACK(%s) gender=%s personality=%s",
                exchange_idx,
                msg.get("for"),
                msg.get("gender"),
                msg.get("personality"),
            )
            continue
        if msg_type == "toolcall":
            ttfb = tracker.record_toolcall()
            if ttfb is not None:
                logger.info("Exchange %02d TOOLCALL ttfb_ms=%.2f", exchange_idx, ttfb)
            continue
        if msg_type == "token":
            chunk = msg.get("text", "")
            metrics = tracker.record_token(chunk)
            chat_ttfb = metrics.get("chat_ttfb_ms")
            if chat_ttfb is not None:
                logger.info("Exchange %02d CHAT ttfb_ms=%.2f", exchange_idx, chat_ttfb)
            first_three = metrics.get("time_to_first_3_words_ms")
            if first_three is not None:
                logger.info("Exchange %02d CHAT time_to_first_3_words_ms=%.2f", exchange_idx, first_three)
            first_sentence = metrics.get("time_to_first_complete_sentence_ms")
            if first_sentence is not None:
                logger.info(
                    "Exchange %02d CHAT time_to_first_complete_sentence_ms=%.2f",
                    exchange_idx,
                    first_sentence,
                )
            continue
        if msg_type == "final":
            normalized = msg.get("normalized_text")
            if normalized:
                tracker.final_text = normalized
            continue
        if msg_type == "done":
            cancelled = bool(msg.get("cancelled"))
            metrics = tracker.finalize_metrics(cancelled)
            logger.info(
                "Exchange %02d metrics: %s",
                exchange_idx,
                json.dumps(metrics, ensure_ascii=False),
            )
            return tracker.final_text
        if msg_type == "error":
            raise RuntimeError(f"Server error: {msg}")
    raise RuntimeError("WebSocket closed before receiving 'done'")


async def run_conversation(
    ws_url: str,
    api_key: str | None,
    prompts: Sequence[str],
    gender: str,
    personality: str,
    recv_timeout: float,
) -> None:
    if not prompts:
        raise ValueError("Conversation prompt list is empty; nothing to send.")

    ws_url_with_auth = with_api_key(ws_url, api_key=api_key)
    chat_prompt = select_chat_prompt(gender)
    session = ConversationSession(
        session_id=f"sess-{uuid.uuid4()}",
        gender=gender,
        personality=personality,
        chat_prompt=chat_prompt,
    )

    logger.info("Connecting to %s (session=%s)", ws_url, session.session_id)
    message_pacer = SlidingWindowPacer(MESSAGE_MAX_PER_WINDOW, MESSAGE_WINDOW_SECONDS)

    async with websockets.connect(
        ws_url_with_auth,
        max_queue=None,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            for idx, user_text in enumerate(prompts, start=1):
                tracker = StreamTracker()
                payload = _build_start_payload(session, user_text)
                logger.info("---- Exchange %02d ----", idx)
                logger.info("User → %r", user_text)
                await message_pacer.wait_turn()
                await ws.send(json.dumps(payload))
                assistant_text = await _stream_exchange(ws, tracker, recv_timeout, idx)
                session.append_exchange(user_text, assistant_text)
                logger.info("Assistant ← %s", assistant_text)
        finally:
            await send_client_end(ws)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    args = _parse_args()
    gender = args.gender or DEFAULT_GENDER
    personality = args.personality or DEFAULT_PERSONALITY
    try:
        asyncio.run(
            run_conversation(
                ws_url=args.server,
                api_key=args.api_key,
                prompts=CONVERSATION_HISTORY_PROMPTS,
                gender=gender,
                personality=personality,
                recv_timeout=args.recv_timeout,
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
