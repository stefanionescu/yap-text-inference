"""Warmup test runner for single-request server testing.

This module provides the run_once function that connects to the WebSocket
server, sends a single request, streams the response, and reports timing
metrics. Used for quick server health checks and warmup validation.
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

import websockets

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
from tests.helpers.errors import ServerError
from tests.helpers.fmt import (
    section_header,
    exchange_header,
    exchange_footer,
    format_user,
    format_assistant,
    format_metrics_inline,
    dim,
    red,
)
from tests.helpers.message import dispatch_message, iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.stream import create_tracker, finalize_metrics, record_token, record_toolcall
from tests.helpers.types import StreamState
from tests.helpers.selection import choose_message
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from tests.messages.warmup import WARMUP_DEFAULT_MESSAGES


# ============================================================================
# Internal Helpers
# ============================================================================


def _build_start_payload(
    session_id: str,
    gender: str,
    personality: str,
    chat_prompt: str,
    user_msg: str,
    sampling: dict[str, float | int] | None,
) -> dict[str, Any]:
    """Build the start message payload."""
    if not chat_prompt:
        raise ValueError(
            "chat_prompt is required for warmup. "
            "Use select_chat_prompt(gender) to get a valid prompt."
        )
    
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": personality,
        "personalities": DEFAULT_PERSONALITIES,
        "chat_prompt": chat_prompt,
        "history": [],
        "user_utterance": user_msg,
    }
    if sampling:
        payload["sampling"] = sampling
    return payload


def _log_unknown_message(msg: dict[str, Any]) -> bool:
    """Ignore unknown message types."""
    return True


def _handle_ack(msg: dict[str, Any], state: StreamState) -> bool:
    """Handle ACK messages."""
    ack_for = msg.get("for")
    if ack_for == "start":
        state.ack_seen = True
    return True


def _handle_toolcall(msg: dict[str, Any], state: StreamState) -> None:
    """Handle toolcall messages."""
    record_toolcall(state)


def _handle_token(msg: dict[str, Any], state: StreamState) -> None:
    """Handle token messages."""
    record_token(state, msg.get("text", ""))


def _handle_final(msg: dict[str, Any], state: StreamState) -> None:
    """Handle final messages with normalized text."""
    normalized = msg.get("normalized_text") or state.final_text
    if normalized:
        state.final_text = normalized


def _handle_done(msg: dict[str, Any], state: StreamState) -> dict[str, Any]:
    """Handle done messages and return metrics."""
    cancelled = bool(msg.get("cancelled"))
    return {"_done": True, "metrics": finalize_metrics(state, cancelled)}


def _handle_error(msg: dict[str, Any], api_key: str) -> None:
    """Handle error messages with helpful hints."""
    error = ServerError.from_message(msg)
    print(f"  {red('ERROR')} {error.error_code}: {error.message}")
    if error.error_code == "authentication_failed":
        print(dim(f"  HINT: Check your TEXT_API_KEY (currently: '{api_key[:8]}...')"))
    elif error.error_code == "server_at_capacity":
        print(dim("  HINT: Server is busy. Try again later."))
    elif error.is_recoverable():
        print(dim(f"  HINT: {error.format_for_user()}"))
    raise error


def _build_stream_handlers(state: StreamState, api_key: str):
    """Build message type handlers for stream processing."""
    return {
        "ack": lambda msg: _handle_ack(msg, state),
        "toolcall": lambda msg: (_handle_toolcall(msg, state) or True),
        "token": lambda msg: (_handle_token(msg, state) or True),
        "final": lambda msg: (_handle_final(msg, state) or True),
        "done": lambda msg: _handle_done(msg, state),
        "error": lambda msg: _handle_error(msg, api_key),
    }


async def _stream_session(
    ws,
    state: StreamState,
    recv_timeout: float,
    api_key: str,
) -> dict[str, Any] | None:
    """Stream the server response and return metrics."""
    handlers = _build_stream_handlers(state, api_key)
    done_payload: dict[str, Any] | None = None
    try:
        async for msg in iter_messages(ws, timeout=recv_timeout):
            result = await dispatch_message(
                msg,
                handlers,
                default=_log_unknown_message,
            )
            if isinstance(result, dict) and result.get("_done"):
                done_payload = result
                break
            if result is False:
                break
    except ServerError:
        raise
    except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
        print(dim("  connection closed by server"))
    except asyncio.TimeoutError:
        print(f"  {red('TIMEOUT')} after {recv_timeout:.1f}s")
    
    if not state.ack_seen:
        print(dim("  warning: no ACK received"))
    
    return done_payload


def _print_transaction_result(
    phase: str | None,
    user_msg: str,
    state: StreamState,
    metrics: dict[str, Any],
) -> None:
    """Print formatted transaction result."""
    if phase:
        print(exchange_header(persona=phase.upper()))
    else:
        print(exchange_header())
    
    print(f"  {format_user(user_msg)}")
    print(f"  {format_assistant(state.final_text)}")
    print(f"  {format_metrics_inline(metrics)}")
    print(exchange_footer())


# ============================================================================
# Public API
# ============================================================================


async def run_once(args) -> None:
    """Execute a single warmup request and report metrics."""
    server_ws_url = args.server or os.getenv("SERVER_WS_URL", DEFAULT_SERVER_WS_URL)
    api_key = args.api_key or os.getenv("TEXT_API_KEY")
    if not api_key:
        raise ValueError("TEXT_API_KEY environment variable is required and must be set before running tests")
    gender_env = os.getenv("GENDER")
    personality_env = os.getenv("PERSONALITY") or os.getenv("PERSONA_STYLE")
    gender = args.gender or gender_env or DEFAULT_GENDER
    personality = args.personality or personality_env or DEFAULT_PERSONALITY
    sampling_overrides = getattr(args, "sampling", None) or None
    double_ttfb = bool(getattr(args, "double_ttfb", False))

    ws_url_with_auth = with_api_key(server_ws_url, api_key=api_key)
    user_msg = choose_message(
        args.message,
        fallback=WARMUP_FALLBACK_MESSAGE,
        defaults=WARMUP_DEFAULT_MESSAGES,
    )
    chat_prompt = select_chat_prompt(gender)
    
    test_name = "WARMUP (double-ttfb)" if double_ttfb else "WARMUP"
    print(f"\n{section_header(test_name)}")
    print(dim(f"  server: {server_ws_url}"))
    print(dim(f"  persona: {personality}/{gender}\n"))

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
                state = create_tracker()
                session_id = str(uuid.uuid4())
                start_payload = _build_start_payload(
                    session_id,
                    gender,
                    personality,
                    chat_prompt,
                    user_msg,
                    sampling_overrides,
                )
                
                await ws.send(json.dumps(start_payload))
                done_payload = await _stream_session(ws, state, recv_timeout, api_key)
                
                metrics = {}
                if done_payload:
                    metrics = done_payload.get("metrics", {})
                else:
                    metrics = finalize_metrics(state, cancelled=True)
                
                _print_transaction_result(phase_label, user_msg, state, metrics)
        finally:
            await send_client_end(ws)


__all__ = ["run_once"]
