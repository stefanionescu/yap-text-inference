from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Any

import websockets

# Add test directory to path for imports
_test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITIES,
    DEFAULT_PERSONALITY,
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_INTERVAL,
    DEFAULT_WS_PING_TIMEOUT,
    WARMUP_FALLBACK_MESSAGE,
)
from tests.helpers.message import dispatch_message, iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.stream import StreamTracker
from tests.helpers.util import choose_message
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from tests.messages.warmup import WARMUP_DEFAULT_MESSAGES

logger = logging.getLogger(__name__)


async def run_once(args) -> None:
    server_ws_url = args.server or os.getenv("SERVER_WS_URL", DEFAULT_SERVER_WS_URL)
    api_key = args.api_key or os.getenv("TEXT_API_KEY")
    if not api_key:
        raise ValueError("TEXT_API_KEY environment variable is required and must be set before running tests")
    gender_env = os.getenv("GENDER")
    personality_env = os.getenv("PERSONALITY") or os.getenv("PERSONA_STYLE")
    gender = args.gender or gender_env or DEFAULT_GENDER
    personality = args.personality or personality_env or DEFAULT_PERSONALITY
    sampling_overrides = getattr(args, "sampling", None) or None
    skip_chat_prompt = bool(getattr(args, "no_chat_prompt", False))
    double_ttfb = bool(getattr(args, "double_ttfb", False))

    ws_url_with_auth = with_api_key(server_ws_url, api_key=api_key)
    user_msg = choose_message(
        args.message,
        fallback=WARMUP_FALLBACK_MESSAGE,
        defaults=WARMUP_DEFAULT_MESSAGES,
    )
    chat_prompt = None if skip_chat_prompt else select_chat_prompt(gender)
    logger.info("Connecting to %s (with API key auth)", server_ws_url)
    async with connect_with_retries(
        lambda: websockets.connect(
            ws_url_with_auth,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        )
    ) as ws:
        recv_timeout = float(os.getenv("RECV_TIMEOUT_SEC", DEFAULT_RECV_TIMEOUT_SEC))
        num_transactions = 2 if double_ttfb else 1
        try:
            for idx in range(num_transactions):
                phase_label = ("first" if idx == 0 else "second") if double_ttfb else None
                tracker = StreamTracker()
                session_id = str(uuid.uuid4())
                start_payload = _build_start_payload(
                    session_id,
                    gender,
                    personality,
                    chat_prompt,
                    user_msg,
                    sampling_overrides,
                )
                if double_ttfb:
                    logger.info("%sSending start message for %s transaction", _phase_prefix(phase_label), phase_label)
                await ws.send(json.dumps(start_payload))
                await _stream_session(ws, tracker, recv_timeout, api_key, phase_label if double_ttfb else None)
        finally:
            await send_client_end(ws)


def _build_start_payload(
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str | None,
    user_msg: str,
    sampling: dict[str, float | int] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": personality,
        "personalities": DEFAULT_PERSONALITIES,
        "history_text": "",
        "user_utterance": user_msg,
    }
    if chat_prompt is not None:
        payload["chat_prompt"] = chat_prompt
    if sampling:
        payload["sampling"] = sampling
    return payload


async def _stream_session(
    ws,
    tracker: StreamTracker,
    recv_timeout: float,
    api_key: str,
    phase_label: str | None = None,
) -> None:
    handlers = _build_stream_handlers(tracker, api_key, phase_label)
    done_seen = False
    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            should_continue = await dispatch_message(
                msg,
                handlers,
                default=lambda payload: _log_unknown_message(payload, phase_label),
            )
            if should_continue is False:
                done_seen = True
                break
    except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
        logger.warning("Connection closed by server")
    except asyncio.TimeoutError:
        logger.error("recv timeout after %.1fs", recv_timeout)
    if not tracker.ack_seen:
        logger.warning("no ACK(start) received from server")
    if not done_seen:
        logger.warning("stream terminated before receiving 'done'")


def _build_stream_handlers(tracker: StreamTracker, api_key: str, phase_label: str | None):
    return {
        "ack": lambda msg: _handle_ack(msg, tracker, phase_label),
        "toolcall": lambda msg: (_handle_toolcall(msg, tracker, phase_label) or True),
        "token": lambda msg: (_handle_token(msg, tracker, phase_label) or True),
        "final": lambda msg: (_handle_final(msg, tracker, phase_label) or True),
        "done": lambda msg: _handle_done(msg, tracker, phase_label),
        "error": lambda msg: _handle_error(msg, api_key, phase_label),
    }


def _log_unknown_message(msg: dict[str, Any], phase_label: str | None) -> bool:
    logger.debug("%sIgnoring message type=%s payload=%s", _phase_prefix(phase_label), msg.get("type"), msg)
    return True


def _handle_ack(msg: dict[str, Any], tracker: StreamTracker, phase_label: str | None) -> bool:
    ack_for = msg.get("for")
    if ack_for == "start":
        tracker.ack_seen = True
        now = msg.get("now")
        gender = msg.get("gender")
        persona = msg.get("personality")
        logger.info("%sACK start → now='%s' gender=%s personality=%s", _phase_prefix(phase_label), now, gender, persona)
    elif ack_for == "set_persona":
        logger.info("%sACK set_persona → %s", _phase_prefix(phase_label), json.dumps(msg, ensure_ascii=False))
    return True


def _handle_toolcall(msg: dict[str, Any], tracker: StreamTracker, phase_label: str | None) -> None:
    status = msg.get("status")
    logger.info("%sTOOLCALL status=%s raw=%s", _phase_prefix(phase_label), status, msg.get("raw"))
    ttfb_ms = tracker.record_toolcall()
    if ttfb_ms is not None:
        logger.info("%sTOOLCALL ttfb_ms=%.2f", _phase_prefix(phase_label), ttfb_ms)


def _handle_token(msg: dict[str, Any], tracker: StreamTracker, phase_label: str | None) -> None:
    chunk = msg.get("text", "")
    metrics = tracker.record_token(chunk)
    chat_ttfb = metrics.get("chat_ttfb_ms")
    if chat_ttfb is not None:
        logger.info("%sCHAT ttfb_ms=%.2f", _phase_prefix(phase_label), chat_ttfb)
    first_3 = metrics.get("time_to_first_3_words_ms")
    if first_3 is not None:
        logger.info("%sCHAT time_to_first_3_words_ms=%.2f", _phase_prefix(phase_label), first_3)
    first_sentence = metrics.get("time_to_first_complete_sentence_ms")
    if first_sentence is not None:
        logger.info("%sCHAT time_to_first_complete_sentence_ms=%.2f", _phase_prefix(phase_label), first_sentence)


def _handle_final(msg: dict[str, Any], tracker: StreamTracker, phase_label: str | None) -> None:
    normalized = msg.get("normalized_text") or tracker.final_text
    if normalized:
        tracker.final_text = normalized


def _handle_done(msg: dict[str, Any], tracker: StreamTracker, phase_label: str | None) -> None:
    cancelled = bool(msg.get("cancelled"))
    metrics_payload = {"type": "metrics", **tracker.finalize_metrics(cancelled)}
    final_text_payload = {"type": "final_text", "text": tracker.final_text}
    if phase_label:
        metrics_payload["phase"] = phase_label
        final_text_payload["phase"] = phase_label
    logger.info(json.dumps(metrics_payload, ensure_ascii=False))
    logger.info(json.dumps(final_text_payload, ensure_ascii=False))
    return False


def _handle_error(msg: dict[str, Any], api_key: str, phase_label: str | None) -> None:
    error_code = msg.get("error_code", "")
    error_message = msg.get("message", "unknown error")
    logger.error("%sServer error %s: %s", _phase_prefix(phase_label), error_code, error_message)
    if error_code == "authentication_failed":
        logger.info("%sHINT: Check your TEXT_API_KEY environment variable (currently: '%s')", _phase_prefix(phase_label), api_key)
    elif error_code == "server_at_capacity":
        logger.info("%sHINT: Server is at maximum connection capacity. Try again later.", _phase_prefix(phase_label))


def _phase_prefix(phase_label: str | None) -> str:
    return f"[{phase_label}] " if phase_label else ""
