from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Awaitable, Callable

_test_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _test_dir not in sys.path:
    sys.path.insert(0, _test_dir)

from tests.helpers.errors import ServerError  # noqa: E402
from tests.helpers.message import dispatch_message, iter_messages  # noqa: E402
from tests.helpers.stream import StreamTracker  # noqa: E402

logger = logging.getLogger(__name__)


async def stream_exchange(
    ws,
    tracker: StreamTracker,
    recv_timeout: float,
    exchange_idx: int,
) -> tuple[str, dict[str, Any]]:
    handlers = _build_exchange_handlers(tracker, exchange_idx)
    done_seen = False
    done_payload: dict[str, Any] | None = None
    async for msg in iter_messages(ws, timeout=recv_timeout):
        should_continue = await dispatch_message(
            msg,
            handlers,
            default=lambda payload: _log_unknown_exchange_message(payload, exchange_idx),
        )
        if isinstance(should_continue, dict) and should_continue.get("_done"):
            done_payload = should_continue
            done_seen = True
            break
        if should_continue is False:
            done_seen = True
            break
    if not done_seen:
        raise RuntimeError("WebSocket closed before receiving 'done'")
    metrics = done_payload.get("metrics") if done_payload else None
    if metrics is None:
        metrics = tracker.finalize_metrics(cancelled=False)
    return tracker.final_text, metrics


def _build_exchange_handlers(tracker: StreamTracker, exchange_idx: int) -> dict[str, Callable[[dict[str, Any]], Awaitable[bool | None] | bool | None]]:
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
    return {"_done": True, "metrics": metrics}


def _handle_error(msg: dict[str, Any]) -> None:
    error_code = msg.get("error_code", "unknown")
    message = msg.get("message", str(msg))
    raise ServerError(error_code, message)


__all__ = ["stream_exchange"]
