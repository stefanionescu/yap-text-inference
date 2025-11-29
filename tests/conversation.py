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
    python3 tests/conversation.py
    python3 tests/conversation.py --server ws://127.0.0.1:8000/ws
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from collections.abc import Sequence

import websockets  # type: ignore[import-not-found]

from tests.helpers.setup import setup_repo_path

setup_repo_path()

from tests.helpers.cli import add_connection_args, add_sampling_args, build_sampling_payload
from tests.helpers.message import dispatch_message, iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.stream import StreamTracker
from tests.helpers.ws import send_client_end, with_api_key
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
)
from tests.messages.conversation import CONVERSATION_HISTORY_MESSAGES
from tests.config.env import get_float_env, get_int_env
from tests.prompts.toolcall import TOOLCALL_PROMPT

logger = logging.getLogger(__name__)


MESSAGE_WINDOW_SECONDS = get_float_env("WS_MESSAGE_WINDOW_SECONDS", 60.0)
MESSAGE_MAX_PER_WINDOW = get_int_env("WS_MAX_MESSAGES_PER_WINDOW", 20)


@dataclass
class ConversationSession:
    session_id: str
    gender: str
    personality: str
    chat_prompt: str
    history: str = ""
    sampling: dict[str, float | int] | None = None

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        transcript = "\n".join(
            chunk for chunk in (self.history, f"User: {user_text}", f"Assistant: {assistant_text}") if chunk
        )
        self.history = transcript.strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Conversation history regression test")
    add_connection_args(
        parser,
        server_help=f"WebSocket URL (default env SERVER_WS_URL or {DEFAULT_SERVER_WS_URL})",
    )
    add_sampling_args(parser)
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
    args = parser.parse_args()
    args.sampling = build_sampling_payload(args)
    return args


def _build_start_payload(session: ConversationSession, user_text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session.session_id,
        "gender": session.gender,
        "personality": session.personality,
        "chat_prompt": session.chat_prompt,
        "history_text": session.history,
        "user_utterance": user_text,
        "tool_prompt": TOOLCALL_PROMPT,
    }
    if session.sampling:
        payload["sampling"] = session.sampling
    return payload


async def _stream_exchange(ws, tracker: StreamTracker, recv_timeout: float, exchange_idx: int) -> str:
    handlers = _build_exchange_handlers(tracker, exchange_idx)
    done_seen = False
    async for msg in iter_messages(ws, timeout=recv_timeout):
        should_continue = await dispatch_message(
            msg,
            handlers,
            default=lambda payload: _log_unknown_exchange_message(payload, exchange_idx),
        )
        if should_continue is False:
            done_seen = True
            break
    if not done_seen:
        raise RuntimeError("WebSocket closed before receiving 'done'")
    return tracker.final_text


def _build_exchange_handlers(tracker: StreamTracker, exchange_idx: int):
    return {
        "ack": lambda msg: _handle_ack(msg, tracker, exchange_idx),
        "toolcall": lambda msg: (_handle_toolcall(msg, tracker, exchange_idx) or True),
        "token": lambda msg: (_handle_token(msg, tracker, exchange_idx) or True),
        "final": lambda msg: (_handle_final(msg, tracker) or True),
        "done": lambda msg: _handle_done(msg, tracker, exchange_idx),
        "error": _handle_error,
    }


def _log_unknown_exchange_message(msg: dict[str, Any], exchange_idx: int) -> bool:
    logger.debug("Exchange %02d ignoring message: %s", exchange_idx, msg)
    return True


def _handle_ack(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> bool:
    tracker.ack_seen = True
    logger.info(
        "Exchange %02d ACK(%s) gender=%s personality=%s",
        exchange_idx,
        msg.get("for"),
        msg.get("gender"),
        msg.get("personality"),
    )
    return True


def _handle_toolcall(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> None:
    ttfb = tracker.record_toolcall()
    logger.info("Exchange %02d TOOLCALL status=%s", exchange_idx, msg.get("status"))
    if ttfb is not None:
        logger.info("Exchange %02d TOOLCALL ttfb_ms=%.2f", exchange_idx, ttfb)


def _handle_token(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> None:
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


def _handle_final(msg: dict[str, Any], tracker: StreamTracker) -> None:
    normalized = msg.get("normalized_text")
    if normalized:
        tracker.final_text = normalized


def _handle_done(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> bool:
    cancelled = bool(msg.get("cancelled"))
    metrics = tracker.finalize_metrics(cancelled)
    logger.info(
        "Exchange %02d metrics: %s",
        exchange_idx,
        json.dumps(metrics, ensure_ascii=False),
    )
    return False


def _handle_error(msg: dict[str, Any]) -> None:
    raise RuntimeError(f"Server error: {msg}")


async def run_conversation(
    ws_url: str,
    api_key: str | None,
    prompts: Sequence[str],
    gender: str,
    personality: str,
    recv_timeout: float,
    sampling: dict[str, float | int] | None,
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
        sampling=sampling,
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
                prompts=CONVERSATION_HISTORY_MESSAGES,
                gender=gender,
                personality=personality,
                recv_timeout=args.recv_timeout,
                sampling=args.sampling or None,
            )
        )
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
