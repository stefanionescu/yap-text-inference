"""Stream processing for conversation exchanges."""

from __future__ import annotations

import logging
from typing import Any
from collections.abc import Awaitable, Callable

from tests.helpers.errors import ServerError
from tests.helpers.message import dispatch_message, iter_messages
from tests.helpers.stream import finalize_metrics, record_token, record_toolcall
from tests.helpers.types import StreamState

logger = logging.getLogger(__name__)

_Handler = Callable[[dict[str, Any]], Awaitable[bool | None] | bool | None]


# ============================================================================
# Internal Helpers
# ============================================================================


def _log_unknown_exchange_message(msg: dict[str, Any], exchange_idx: int) -> bool:
    logger.debug("Exchange %02d ignoring message: %s", exchange_idx, msg)
    return True


def _handle_ack(msg: dict[str, Any], state: StreamState, exchange_idx: int) -> bool:
    state.ack_seen = True
    return True


def _handle_toolcall(msg: dict[str, Any], state: StreamState, exchange_idx: int) -> None:
    record_toolcall(state)


def _handle_token(msg: dict[str, Any], state: StreamState, exchange_idx: int) -> None:
    record_token(state, msg.get("text", ""))


def _handle_final(msg: dict[str, Any], state: StreamState) -> None:
    normalized = msg.get("normalized_text")
    if normalized:
        state.final_text = normalized


def _handle_done(msg: dict[str, Any], state: StreamState, exchange_idx: int) -> bool:
    cancelled = bool(msg.get("cancelled"))
    metrics = finalize_metrics(state, cancelled)
    return {"_done": True, "metrics": metrics}


def _handle_error(msg: dict[str, Any]) -> None:
    raise ServerError.from_message(msg)


def _build_exchange_handlers(state: StreamState, exchange_idx: int) -> dict[str, _Handler]:
    return {
        "ack": lambda msg: _handle_ack(msg, state, exchange_idx),
        "toolcall": lambda msg: (_handle_toolcall(msg, state, exchange_idx) or True),
        "token": lambda msg: (_handle_token(msg, state, exchange_idx) or True),
        "final": lambda msg: (_handle_final(msg, state) or True),
        "done": lambda msg: _handle_done(msg, state, exchange_idx),
        "error": _handle_error,
    }


# ============================================================================
# Public API
# ============================================================================


async def stream_exchange(
    ws,
    state: StreamState,
    recv_timeout: float,
    exchange_idx: int,
) -> tuple[str, dict[str, Any]]:
    """Stream a single exchange and return the assistant response and metrics."""
    handlers = _build_exchange_handlers(state, exchange_idx)
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
        metrics = finalize_metrics(state, cancelled=False)
    return state.final_text, metrics


__all__ = ["stream_exchange"]
