from __future__ import annotations

import logging
from typing import Any
from collections.abc import Awaitable, Callable

from tests.helpers.errors import ServerError
from tests.helpers.fmt import format_metrics_inline
from tests.helpers.message import dispatch_message, iter_messages
from tests.helpers.stream import StreamTracker

logger = logging.getLogger(__name__)

# Type alias for message handler functions
_Handler = Callable[[dict[str, Any]], Awaitable[bool | None] | bool | None]


# ============================================================================
# Internal Helpers
# ============================================================================


def _log_unknown_exchange_message(msg: dict[str, Any], exchange_idx: int) -> bool:
    logger.debug("Exchange %02d ignoring message: %s", exchange_idx, msg)
    return True


def _handle_ack(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> bool:
    tracker.ack_seen = True
    # Silently acknowledge - no need for verbose output
    return True


def _handle_toolcall(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> None:
    tracker.record_toolcall()
    # Silently record - metrics shown at end


def _handle_token(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> None:
    chunk = msg.get("text", "")
    tracker.record_token(chunk)
    # Silently record - metrics shown at end


def _handle_final(msg: dict[str, Any], tracker: StreamTracker) -> None:
    normalized = msg.get("normalized_text")
    if normalized:
        tracker.final_text = normalized


def _handle_done(msg: dict[str, Any], tracker: StreamTracker, exchange_idx: int) -> bool:
    cancelled = bool(msg.get("cancelled"))
    metrics = tracker.finalize_metrics(cancelled)
    return {"_done": True, "metrics": metrics}


def _handle_error(msg: dict[str, Any]) -> None:
    raise ServerError.from_message(msg)


def _build_exchange_handlers(tracker: StreamTracker, exchange_idx: int) -> dict[str, _Handler]:
    return {
        "ack": lambda msg: _handle_ack(msg, tracker, exchange_idx),
        "toolcall": lambda msg: (_handle_toolcall(msg, tracker, exchange_idx) or True),
        "token": lambda msg: (_handle_token(msg, tracker, exchange_idx) or True),
        "final": lambda msg: (_handle_final(msg, tracker) or True),
        "done": lambda msg: _handle_done(msg, tracker, exchange_idx),
        "error": _handle_error,
    }


# ============================================================================
# Public API
# ============================================================================


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


__all__ = ["stream_exchange"]
