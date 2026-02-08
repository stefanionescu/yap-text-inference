"""WebSocket connection handling for benchmark transactions.

This module provides the core transaction execution logic over WebSocket
connections. It handles connection setup, message sending, response streaming,
and error handling for benchmark runs.
"""

from __future__ import annotations

import json
import uuid
import asyncio
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

from tests.state import StreamState, SessionContext, BenchmarkConfig
from tests.config import WS_MAX_QUEUE
from tests.helpers.metrics import error_result
from tests.helpers.websocket import (
    record_token,
    with_api_key,
    iter_messages,
    create_tracker,
    record_toolcall,
    send_client_end,
    finalize_metrics,
    build_start_payload,
    connect_with_retries,
)


async def _execute_phase(
    ws,
    cfg: BenchmarkConfig,
    phase: int,
    session_id: str,
) -> dict[str, Any]:
    """Execute a single transaction phase with timeout handling."""
    try:
        return await asyncio.wait_for(
            _send_and_stream(ws, cfg, phase, session_id),
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
    session_id: str,
) -> dict[str, Any]:
    """Send a start message and stream the response."""
    if cfg.chat_prompt is None:
        raise ValueError("chat_prompt is required for benchmark. Use select_chat_prompt(gender) to get a valid prompt.")
    ctx = SessionContext(
        session_id=session_id,
        gender=cfg.gender,
        personality=cfg.style,
        chat_prompt=cfg.chat_prompt,
        sampling=cfg.sampling,
    )
    payload = build_start_payload(ctx, cfg.message)
    state = create_tracker()

    await ws.send(json.dumps(payload))
    return await _consume_stream(ws, state, phase)


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
                # Capture toolcall result for tool-only mode
                state.toolcall_status = msg.get("status")
                state.toolcall_raw = msg.get("raw")
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
                metrics = finalize_metrics(state, cancelled=False)
                return _build_success_result(metrics, phase)

            if msg_type == "cancelled":
                metrics = finalize_metrics(state, cancelled=True)
                return _build_success_result(metrics, phase)

            if msg_type == "error":
                return _build_error_result(msg, phase)

    except ConnectionClosedOK:
        return error_result("connection_closed_ok", phase=phase)
    except ConnectionClosedError as exc:
        return error_result(f"connection_closed: code={exc.code}", phase=phase)

    return error_result("stream ended before 'done'", phase=phase)


def _build_success_result(metrics: dict[str, Any], phase: int) -> dict[str, Any]:
    """Build a success result from tracker metrics."""
    return {
        "ok": metrics.get("ok", True),
        "phase": phase,
        "ttfb_toolcall_ms": metrics.get("ttfb_toolcall_ms"),
        "ttfb_chat_ms": metrics.get("ttfb_chat_ms"),
        "first_sentence_ms": metrics.get("time_to_first_complete_sentence_ms"),
        "first_3_words_ms": metrics.get("time_to_first_3_words_ms"),
    }


def _build_error_result(msg: dict[str, Any], phase: int) -> dict[str, Any]:
    """Build an error result from a server error message."""
    from tests.helpers.errors import ServerError  # noqa: PLC0415

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

    session_id = f"bench-{uuid.uuid4()}"
    try:
        async with connect_with_retries(lambda: websockets.connect(auth_url, max_queue=WS_MAX_QUEUE)) as ws:
            try:
                for phase in range(1, phases + 1):
                    result = await _execute_phase(ws, cfg, phase, session_id)
                    results.append(result)
                    if not result.get("ok"):
                        break
            finally:
                await send_client_end(ws, session_id)
    except (ConnectionClosedOK, ConnectionClosedError) as exc:
        if not results:
            return [error_result(f"connection_closed: {exc}", phase=1)]
    except Exception as exc:
        if not results:
            return [error_result(f"connection_failed: {exc}", phase=1)]

    return results if results else [error_result("connection_failed", phase=1)]


__all__ = ["execute_connection"]
