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
from tests.helpers.metrics import SessionContext, StreamState
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.selection import choose_message
from tests.helpers.websocket import (
    build_start_payload,
    connect_with_retries,
    create_tracker,
    finalize_metrics,
    send_client_end,
    with_api_key,
)
from tests.messages.warmup import WARMUP_DEFAULT_MESSAGES
from tests.logic.conversation.stream import stream_exchange


def _print_server_error_hint(error: ServerError, api_key: str) -> None:
    """Print human-friendly hints for server errors."""
    print(f"  {red('ERROR')} {error.error_code}: {error.message}")
    if error.error_code == "authentication_failed":
        preview = f"{api_key[:8]}..." if api_key else "missing"
        print(dim(f"  HINT: Check your TEXT_API_KEY (currently: '{preview}')"))
    elif error.error_code == "server_at_capacity":
        print(dim("  HINT: Server is busy. Try again later."))
    elif error.is_recoverable():
        print(dim(f"  HINT: {error.format_for_user()}"))


async def _stream_exchange(
    ws,
    state: StreamState,
    recv_timeout: float,
    api_key: str,
    exchange_idx: int,
) -> tuple[str, dict[str, Any]]:
    """Consume a single exchange, returning assistant text and metrics."""
    suppress_ack_warning = False
    try:
        assistant_text, metrics = await stream_exchange(
            ws,
            state,
            recv_timeout,
            exchange_idx,
        )
        return assistant_text, metrics
    except ServerError as error:
        suppress_ack_warning = True
        _print_server_error_hint(error, api_key)
        raise
    except (websockets.ConnectionClosedOK, websockets.ConnectionClosedError):
        print(dim("  connection closed by server"))
    except asyncio.TimeoutError:
        print(f"  {red('TIMEOUT')} after {recv_timeout:.1f}s")
    finally:
        if not suppress_ack_warning and not state.ack_seen:
            print(dim("  warning: no ACK received"))

    return state.final_text, finalize_metrics(state, cancelled=True)


def _print_transaction_result(
    phase: str | None,
    user_msg: str,
    assistant_text: str,
    metrics: dict[str, Any],
) -> None:
    """Print formatted transaction result."""
    if phase:
        print(exchange_header(persona=phase.upper()))
    else:
        print(exchange_header())
    
    print(f"  {format_user(user_msg)}")
    print(f"  {format_assistant(assistant_text)}")
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
                ctx = SessionContext(
                    session_id=session_id,
                    gender=gender,
                    personality=personality,
                    chat_prompt=chat_prompt,
                    sampling=sampling_overrides,
                )
                start_payload = build_start_payload(ctx, user_msg)
                
                await ws.send(json.dumps(start_payload))
                assistant_text, metrics = await _stream_exchange(
                    ws,
                    state,
                    recv_timeout,
                    api_key,
                    exchange_idx=idx + 1,
                )
                _print_transaction_result(phase_label, user_msg, assistant_text, metrics)
        finally:
            await send_client_end(ws)


__all__ = ["run_once"]
