from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

# Add test directory to path for imports
_test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    WARMUP_FALLBACK_MESSAGE,
)
from tests.messages.warmup import WARMUP_DEFAULT_MESSAGES
from tests.helpers.message import iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.regex import contains_complete_sentence, has_at_least_n_words
from tests.helpers.util import choose_message
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from tests.prompts.toolcall import TOOLCALL_PROMPT

logger = logging.getLogger(__name__)


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
            "type": "metrics",
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

    def final_text_payload(self) -> dict[str, Any]:
        return {"type": "final_text", "text": self.final_text}


def _round(value: float | None) -> float | None:
    return round(value, 2) if value is not None else None


async def run_once(args) -> None:
    server_ws_url = args.server or os.getenv("SERVER_WS_URL", DEFAULT_SERVER_WS_URL)
    api_key = args.api_key or os.getenv("TEXT_API_KEY")
    if not api_key:
        raise ValueError("TEXT_API_KEY environment variable is required and must be set before running tests")
    gender = args.gender or os.getenv("GENDER", DEFAULT_GENDER)
    personality = args.personality or os.getenv("PERSONALITY", DEFAULT_PERSONALITY)
    sampling_overrides = getattr(args, "sampling", None) or None

    ws_url_with_auth = with_api_key(server_ws_url, api_key=api_key)
    user_msg = choose_message(
        args.message,
        fallback=WARMUP_FALLBACK_MESSAGE,
        defaults=WARMUP_DEFAULT_MESSAGES,
    )
    session_id = str(uuid.uuid4())
    chat_prompt = select_chat_prompt(gender)
    start_payload = _build_start_payload(
        session_id, gender, personality, chat_prompt, user_msg, sampling_overrides
    )

    logger.info("Connecting to %s (with API key auth)", server_ws_url)
    async with connect_with_retries(
        lambda: websockets.connect(
            ws_url_with_auth,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        )
    ) as ws:
        tracker = StreamTracker()
        recv_timeout = float(os.getenv("RECV_TIMEOUT_SEC", DEFAULT_RECV_TIMEOUT_SEC))
        try:
            await ws.send(json.dumps(start_payload))
            await _stream_session(ws, tracker, recv_timeout, api_key)
        finally:
            await send_client_end(ws)


def _build_start_payload(
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    user_msg: str,
    sampling: dict[str, float | int] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": personality,
        "chat_prompt": chat_prompt,
        "history_text": "",
        "user_utterance": user_msg,
        "tool_prompt": TOOLCALL_PROMPT,
    }
    if sampling:
        payload["sampling"] = sampling
    return payload


async def _stream_session(ws, tracker: StreamTracker, recv_timeout: float, api_key: str) -> None:
    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            if not _process_message(msg, tracker, api_key):
                break
    except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
        logger.warning("Connection closed by server")
    except asyncio.TimeoutError:
        logger.error("recv timeout after %.1fs", recv_timeout)
    if not tracker.ack_seen:
        logger.warning("no ACK(start) received from server")


def _process_message(msg: dict[str, Any], tracker: StreamTracker, api_key: str) -> bool:
    t = msg.get("type")
    if t == "ack":
        return _handle_ack(msg, tracker)
    if t == "toolcall":
        _handle_toolcall(msg, tracker)
        return True
    if t == "token":
        _handle_token(msg, tracker)
        return True
    if t == "final":
        _handle_final(msg, tracker)
        return True
    if t == "done":
        _handle_done(msg, tracker)
        return False
    if t == "error":
        _handle_error(msg, api_key)
        return False
    return True


def _handle_ack(msg: dict[str, Any], tracker: StreamTracker) -> bool:
    ack_for = msg.get("for")
    if ack_for == "start":
        tracker.ack_seen = True
        now = msg.get("now")
        gender = msg.get("gender")
        persona = msg.get("personality")
        logger.info("ACK start → now='%s' gender=%s personality=%s", now, gender, persona)
    elif ack_for == "set_persona":
        logger.info("ACK set_persona → %s", json.dumps(msg, ensure_ascii=False))
    return True


def _handle_toolcall(msg: dict[str, Any], tracker: StreamTracker) -> None:
    status = msg.get("status")
    logger.info("TOOLCALL status=%s raw=%s", status, msg.get("raw"))
    ttfb_ms = tracker.record_toolcall()
    if ttfb_ms is not None:
        logger.info("TOOLCALL ttfb_ms=%.2f", ttfb_ms)


def _handle_token(msg: dict[str, Any], tracker: StreamTracker) -> None:
    chunk = msg.get("text", "")
    metrics = tracker.record_token(chunk)
    chat_ttfb = metrics.get("chat_ttfb_ms")
    if chat_ttfb is not None:
        logger.info("CHAT ttfb_ms=%.2f", chat_ttfb)
    first_3 = metrics.get("time_to_first_3_words_ms")
    if first_3 is not None:
        logger.info("CHAT time_to_first_3_words_ms=%.2f", first_3)
    first_sentence = metrics.get("time_to_first_complete_sentence_ms")
    if first_sentence is not None:
        logger.info("CHAT time_to_first_complete_sentence_ms=%.2f", first_sentence)


def _handle_final(msg: dict[str, Any], tracker: StreamTracker) -> None:
    normalized = msg.get("normalized_text") or tracker.final_text
    if normalized:
        tracker.final_text = normalized


def _handle_done(msg: dict[str, Any], tracker: StreamTracker) -> None:
    cancelled = bool(msg.get("cancelled"))
    logger.info(json.dumps(tracker.finalize_metrics(cancelled), ensure_ascii=False))
    logger.info(json.dumps(tracker.final_text_payload(), ensure_ascii=False))


def _handle_error(msg: dict[str, Any], api_key: str) -> None:
    error_code = msg.get("error_code", "")
    error_message = msg.get("message", "unknown error")
    logger.error("Server error %s: %s", error_code, error_message)
    if error_code == "authentication_failed":
        logger.info("HINT: Check your TEXT_API_KEY environment variable (currently: '%s')", api_key)
    elif error_code == "server_at_capacity":
        logger.info("HINT: Server is at maximum connection capacity. Try again later.")


