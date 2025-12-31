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

from tests.config import DEFAULT_PERSONALITIES
from tests.helpers.message import iter_messages
from tests.helpers.results import error_result
from tests.helpers.stream import StreamTracker
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key

from .types import BenchmarkConfig

WS_MAX_QUEUE = None


async def _open_connection(auth_url: str):
    """Open a WebSocket connection with retry logic.
    
    Returns the WebSocket or None if connection fails.
    """
    try:
        ctx = connect_with_retries(
            lambda: websockets.connect(auth_url, max_queue=WS_MAX_QUEUE)
        )
        return await ctx.__aenter__()
    except Exception:
        return None


async def _close_connection(ws) -> None:
    """Close a WebSocket connection gracefully."""
    try:
        await send_client_end(ws)
    except Exception:
        pass
    try:
        await ws.close()
    except Exception:
        pass


async def _execute_phase(
    ws,
    cfg: BenchmarkConfig,
    phase: int,
) -> dict[str, Any]:
    """Execute a single transaction phase with timeout handling.
    
    Args:
        ws: Open WebSocket connection.
        cfg: Benchmark configuration.
        phase: Phase number (1 or 2).
    
    Returns:
        Result dict with ok status and metrics or error.
    """
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
    """Send a start message and stream the response.
    
    Args:
        ws: Open WebSocket connection.
        cfg: Benchmark configuration.
        phase: Phase number for result tagging.
    
    Returns:
        Result dict with metrics on success or error details on failure.
    """
    session_id = str(uuid.uuid4())
    payload = _build_payload(session_id, cfg)
    tracker = StreamTracker()

    await ws.send(json.dumps(payload))
    return await _consume_stream(ws, tracker, phase)


def _build_payload(session_id: str, cfg: BenchmarkConfig) -> dict[str, Any]:
    """Build the start message payload."""
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": cfg.gender,
        "personality": cfg.style,
        "personalities": DEFAULT_PERSONALITIES,
        "history_text": "",
        "user_utterance": cfg.message,
    }
    if cfg.chat_prompt is not None:
        payload["chat_prompt"] = cfg.chat_prompt
    if cfg.sampling:
        payload["sampling"] = cfg.sampling
    return payload


async def _consume_stream(
    ws,
    tracker: StreamTracker,
    phase: int,
) -> dict[str, Any]:
    """Consume the response stream and collect metrics.
    
    Args:
        ws: Open WebSocket connection.
        tracker: StreamTracker for timing metrics.
        phase: Phase number for result tagging.
    
    Returns:
        Result dict with metrics on success or error details on failure.
    """
    async for msg in iter_messages(ws):
        msg_type = msg.get("type")

        if msg_type == "toolcall":
            tracker.record_toolcall()
            continue

        if msg_type == "token":
            tracker.record_token(msg.get("text", ""))
            continue

        if msg_type == "final":
            normalized = msg.get("normalized_text")
            if normalized:
                tracker.final_text = normalized
            continue

        if msg_type == "done":
            cancelled = bool(msg.get("cancelled"))
            return _build_success_result(tracker, phase, cancelled)

        if msg_type == "error":
            return _build_error_result(msg, phase)

    return error_result("stream ended before 'done'", phase=phase)


def _build_success_result(
    tracker: StreamTracker,
    phase: int,
    cancelled: bool,
) -> dict[str, Any]:
    """Build a success result from tracker metrics."""
    return {
        "ok": not cancelled,
        "phase": phase,
        "ttfb_toolcall_ms": tracker.toolcall_ttfb_ms,
        "ttfb_chat_ms": tracker._ms_since_sent(tracker.first_token_ts),
        "first_sentence_ms": tracker._ms_since_sent(tracker.first_sentence_ts),
        "first_3_words_ms": tracker._ms_since_sent(tracker.first_3_words_ts),
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
    """Execute one or two transactions over a single WebSocket connection.
    
    This is a flattened version of the previous deeply-nested _one_connection.
    Error handling is simplified by using early returns and helper functions.
    
    Args:
        cfg: Benchmark configuration with all connection parameters.
    
    Returns:
        List of result dicts, one per transaction phase.
    """
    phases = 2 if cfg.double_ttfb else 1
    results: list[dict[str, Any]] = []
    auth_url = with_api_key(cfg.url, api_key=cfg.api_key)

    ws = await _open_connection(auth_url)
    if ws is None:
        return [error_result("connection_failed", phase=1)]

    try:
        for phase in range(1, phases + 1):
            result = await _execute_phase(ws, cfg, phase)
            results.append(result)
            if not result.get("ok"):
                break
    finally:
        await _close_connection(ws)

    return results


__all__ = ["execute_connection"]

