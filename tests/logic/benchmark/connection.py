"""WebSocket connection handling for benchmark transactions.

This module provides the core transaction execution logic over WebSocket
connections. It handles connection setup, message sending, response streaming,
and error handling for benchmark runs.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from tests.config import WS_MAX_QUEUE
from tests.helpers.metrics import StreamState, error_result
from tests.helpers.websocket import (
    connect_with_retries,
    create_tracker,
    iter_messages,
    record_token,
    record_toolcall,
    send_client_end,
    with_api_key,
)

from .types import BenchmarkConfig


def _ms_since_sent(state: StreamState, timestamp: float | None) -> float | None:
    """Calculate milliseconds elapsed since the request was sent."""
    if timestamp is None:
        return None
    return (timestamp - state.sent_ts) * 1000.0


async def _execute_phase(
    ws,
    cfg: BenchmarkConfig,
    phase: int,
) -> dict[str, Any]:
    """Execute a single transaction phase with timeout handling."""
    try:
        return await asyncio.wait_for(
            _send_and_stream(ws, cfg, phase),
            timeout=cfg.timeout_s,
        )
    except asyncio.TimeoutError:
        return error_result("timeout", phase=phase)
    except Exception as exc:
        return error_result(str(exc), phase=phase)


async def _send_and_stream(
    ws,
    cfg: BenchmarkConfig,
    phase: int,
) -> dict[str, Any]:
    """Send a start message and stream the response."""
    session_id = str(uuid.uuid4())
    payload = _build_payload(session_id, cfg)
    state = create_tracker()

    await ws.send(json.dumps(payload))
    return await _consume_stream(ws, state, phase)


def _build_payload(session_id: str, cfg: BenchmarkConfig) -> dict[str, Any]:
    """Build the start message payload."""
    if cfg.chat_prompt is None:
        raise ValueError(
            "chat_prompt is required for benchmark. "
            "Use select_chat_prompt(gender) to get a valid prompt."
        )
    
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": cfg.gender,
        "personality": cfg.style,
        "chat_prompt": cfg.chat_prompt,
        "history": [],
        "user_utterance": cfg.message,
    }
    if cfg.sampling:
        payload["sampling"] = cfg.sampling
    return payload


async def _consume_stream(
    ws,
    state: StreamState,
    phase: int,
) -> dict[str, Any]:
    """Consume the response stream and collect metrics."""
    try:
        async for msg in iter_messages(ws):
            msg_type = msg.get("type")

            if msg_type == "toolcall":
                record_toolcall(state)
                continue

            if msg_type == "token":
                record_token(state, msg.get("text", ""))
                continue

            if msg_type == "final":
                normalized = msg.get("normalized_text")
                if normalized:
                    state.final_text = normalized
                continue

            if msg_type == "done":
                cancelled = bool(msg.get("cancelled"))
                return _build_success_result(state, phase, cancelled)

            if msg_type == "error":
                return _build_error_result(msg, phase)

    except ConnectionClosedOK:
        return error_result("connection_closed_ok", phase=phase)
    except ConnectionClosedError as exc:
        return error_result(f"connection_closed: code={exc.code}", phase=phase)

    return error_result("stream ended before 'done'", phase=phase)


def _build_success_result(
    state: StreamState,
    phase: int,
    cancelled: bool,
) -> dict[str, Any]:
    """Build a success result from tracker metrics."""
    return {
        "ok": not cancelled,
        "phase": phase,
        "ttfb_toolcall_ms": state.toolcall_ttfb_ms,
        "ttfb_chat_ms": _ms_since_sent(state, state.first_token_ts),
        "first_sentence_ms": _ms_since_sent(state, state.first_sentence_ts),
        "first_3_words_ms": _ms_since_sent(state, state.first_3_words_ts),
    }


def _build_error_result(msg: dict[str, Any], phase: int) -> dict[str, Any]:
    """Build an error result from a server error message."""
    from tests.helpers.errors import ServerError
    error = ServerError.from_message(msg)
    return {
        "ok": False,
        "phase": phase,
        "error": str(error),
        "error_code": error.error_code,
        "recoverable": error.is_recoverable(),
    }


async def execute_connection(cfg: BenchmarkConfig) -> list[dict[str, Any]]:
    """Execute one or two transactions over a single WebSocket connection."""
    phases = 2 if cfg.double_ttfb else 1
    results: list[dict[str, Any]] = []
    auth_url = with_api_key(cfg.url, api_key=cfg.api_key)

    try:
        async with connect_with_retries(
            lambda: websockets.connect(auth_url, max_queue=WS_MAX_QUEUE)
        ) as ws:
            try:
                for phase in range(1, phases + 1):
                    result = await _execute_phase(ws, cfg, phase)
                    results.append(result)
                    if not result.get("ok"):
                        break
            finally:
                await send_client_end(ws)
    except (ConnectionClosedOK, ConnectionClosedError) as exc:
        if not results:
            return [error_result(f"connection_closed: {exc}", phase=1)]
    except Exception as exc:
        if not results:
            return [error_result(f"connection_failed: {exc}", phase=1)]

    return results if results else [error_result("connection_failed", phase=1)]


__all__ = ["execute_connection"]
