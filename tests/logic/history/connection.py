"""WebSocket connection handling for history benchmark transactions.

This module provides transaction execution logic for history benchmarks.
Each connection starts with warm history and cycles through recall messages.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from tests.config import DEFAULT_PERSONALITIES
from tests.helpers.message import iter_messages
from tests.helpers.results import error_result
from tests.helpers.stream import StreamTracker
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from tests.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES

from .types import HistoryBenchConfig

WS_MAX_QUEUE = None


def _build_payload(
    session_id: str,
    cfg: HistoryBenchConfig,
    history: list[dict[str, str]],
    user_text: str,
) -> dict[str, Any]:
    """Build the start message payload with history."""
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": cfg.gender,
        "personality": cfg.personality,
        "personalities": DEFAULT_PERSONALITIES,
        "chat_prompt": cfg.chat_prompt,
        "history": history,
        "user_utterance": user_text,
    }
    if cfg.sampling:
        payload["sampling"] = cfg.sampling
    return payload


async def _wait_for_ack(ws) -> None:
    """Wait for ack message, discarding history info."""
    async for msg in iter_messages(ws):
        if msg.get("type") == "ack":
            return
        if msg.get("type") == "error":
            raise RuntimeError(f"Server error: {msg}")


async def _consume_stream(ws, tracker: StreamTracker) -> str:
    """Consume streaming response until done, tracking metrics."""
    async for msg in iter_messages(ws):
        msg_type = msg.get("type")

        if msg_type == "toolcall":
            tracker.record_toolcall()
            continue

        if msg_type == "token":
            tracker.record_token(msg.get("text", ""))
            continue

        if msg_type == "final":
            if msg.get("normalized_text"):
                tracker.final_text = msg["normalized_text"]
            continue

        if msg_type == "done":
            return tracker.final_text

        if msg_type == "error":
            raise RuntimeError(f"Server error: {msg}")

    raise RuntimeError("Stream ended before 'done'")


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
    payload = _build_payload(session_id, cfg, history, user_text)
    tracker = StreamTracker()

    await ws.send(json.dumps(payload))
    await _wait_for_ack(ws)
    reply = await _consume_stream(ws, tracker)

    return {
        "ok": True,
        "phase": phase,
        "reply": reply,
        "ttfb_toolcall_ms": tracker.toolcall_ttfb_ms,
        "ttfb_chat_ms": tracker._ms_since_sent(tracker.first_token_ts),
        "first_sentence_ms": tracker._ms_since_sent(tracker.first_sentence_ts),
        "first_3_words_ms": tracker._ms_since_sent(tracker.first_3_words_ts),
    }


async def execute_history_connection(cfg: HistoryBenchConfig) -> list[dict[str, Any]]:
    """Execute multiple transactions over a single WebSocket connection.

    Each connection starts with WARM_HISTORY and cycles through all
    HISTORY_RECALL_MESSAGES, building conversation as it goes.

    Args:
        cfg: History benchmark configuration.

    Returns:
        List of result dicts, one per recall message.
    """
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

                    # Append exchange to history for next transaction
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

