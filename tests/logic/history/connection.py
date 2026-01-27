"""WebSocket connection handling for history benchmark transactions.

This module provides transaction execution logic for history benchmarks.
Each connection starts with warm history and cycles through recall messages.
"""

from __future__ import annotations

import json
import uuid
import asyncio
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from tests.config import WS_MAX_QUEUE
from tests.helpers.errors import StreamError
from tests.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES
from tests.helpers.metrics import StreamState, SessionContext, error_result
from tests.helpers.websocket import (
    with_api_key,
    iter_messages,
    consume_stream,
    create_tracker,
    send_client_end,
    finalize_metrics,
    build_start_payload,
    connect_with_retries,
)

from .types import HistoryBenchConfig


async def _wait_for_ack(ws) -> None:
    """Wait for ack message, discarding history info."""
    async for msg in iter_messages(ws):
        if msg.get("type") == "ack":
            return
        if msg.get("type") == "error":
            raise RuntimeError(f"Server error: {msg}")


async def _consume_stream_wrapper(ws, state: StreamState) -> str:
    """Consume streaming response until done, tracking metrics."""
    try:
        return await consume_stream(ws, state)
    except StreamError as exc:
        raise RuntimeError(f"Server error: {exc.message}") from exc


async def _execute_transaction(
    ws,
    cfg: HistoryBenchConfig,
    session_id: str,
    history: list[dict[str, str]],
    user_text: str,
    phase: int,
) -> dict[str, Any]:
    """Execute a single transaction with timeout handling."""
    try:
        return await asyncio.wait_for(
            _send_and_stream(ws, cfg, session_id, history, user_text, phase),
            timeout=cfg.timeout_s,
        )
    except asyncio.TimeoutError:
        return error_result("timeout", phase=phase)
    except Exception as exc:
        return error_result(str(exc), phase=phase)


async def _send_and_stream(
    ws,
    cfg: HistoryBenchConfig,
    session_id: str,
    history: list[dict[str, str]],
    user_text: str,
    phase: int,
) -> dict[str, Any]:
    """Send a start message and stream the response."""
    ctx = SessionContext(
        session_id=session_id,
        gender=cfg.gender,
        personality=cfg.personality,
        chat_prompt=cfg.chat_prompt,
        sampling=cfg.sampling,
    )
    payload = build_start_payload(ctx, user_text, history=history)
    state = create_tracker()

    await ws.send(json.dumps(payload))
    await _wait_for_ack(ws)
    reply = await _consume_stream_wrapper(ws, state)

    metrics = finalize_metrics(state)
    return {
        "ok": metrics.get("ok", True),
        "phase": phase,
        "reply": reply,
        "ttfb_toolcall_ms": metrics.get("ttfb_toolcall_ms"),
        "ttfb_chat_ms": metrics.get("ttfb_chat_ms"),
        "first_sentence_ms": metrics.get("time_to_first_complete_sentence_ms"),
        "first_3_words_ms": metrics.get("time_to_first_3_words_ms"),
    }


async def execute_history_connection(cfg: HistoryBenchConfig) -> list[dict[str, Any]]:
    """Execute multiple transactions over a single WebSocket connection."""
    results: list[dict[str, Any]] = []
    auth_url = with_api_key(cfg.url, api_key=cfg.api_key)
    session_id = f"history-bench-{uuid.uuid4()}"
    history: list[dict[str, str]] = list(WARM_HISTORY)

    try:
        async with connect_with_retries(
            lambda: websockets.connect(auth_url, max_queue=WS_MAX_QUEUE)
        ) as ws:
            try:
                for phase, user_text in enumerate(HISTORY_RECALL_MESSAGES, 1):
                    result = await _execute_transaction(
                        ws, cfg, session_id, history, user_text, phase
                    )
                    results.append(result)

                    if not result.get("ok"):
                        break

                    reply = result.get("reply", "")
                    history.append({"role": "user", "content": user_text})
                    history.append({"role": "assistant", "content": reply})
            finally:
                await send_client_end(ws)
    except (ConnectionClosedOK, ConnectionClosedError) as exc:
        if not results:
            return [error_result(f"connection_closed: {exc}", phase=1)]
    except Exception as exc:
        if not results:
            return [error_result(f"connection_failed: {exc}", phase=1)]

    return results if results else [error_result("connection_failed", phase=1)]


__all__ = ["execute_history_connection"]
