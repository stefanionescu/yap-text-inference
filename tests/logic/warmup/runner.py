"""Warmup test runner for single-request server testing.

This module provides the run_once function that connects to the WebSocket
server, sends a single request, streams the response, and reports timing
metrics. Used for quick server health checks and warmup validation.
"""

from __future__ import annotations

import os
import json
import uuid
import asyncio
from typing import Any

import websockets

from tests.helpers.errors import ServerError
from tests.helpers.selection import choose_message
from tests.helpers.prompt import select_chat_prompt
from tests.state import StreamState, SessionContext
from tests.messages.warmup import WARMUP_DEFAULT_MESSAGES
from tests.logic.conversation.stream import stream_exchange
from tests.helpers.websocket import (
    with_api_key,
    create_tracker,
    send_client_end,
    finalize_metrics,
    build_start_payload,
    connect_with_retries,
)
from tests.helpers.fmt import (
    dim,
    red,
    format_user,
    section_header,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_metrics_inline,
)
from tests.config import (
    DEFAULT_GENDER,
    DEFAULT_PERSONALITY,
    DEFAULT_SERVER_WS_URL,
    DEFAULT_WS_PING_TIMEOUT,
    WARMUP_FALLBACK_MESSAGE,
    DEFAULT_RECV_TIMEOUT_SEC,
    DEFAULT_WS_PING_INTERVAL,
)


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


def _format_tool_result(state: StreamState) -> str:
    """Format tool-only result for display."""
    if state.toolcall_status:
        raw = state.toolcall_raw or {}
        decision = raw.get("text", state.toolcall_status)
        return f"[tool: {decision}]"
    return "[tool: no response]"


def _print_transaction_result(
    phase: str | None,
    user_msg: str,
    assistant_text: str,
    metrics: dict[str, Any],
    state: StreamState | None = None,
) -> None:
    """Print formatted transaction result."""
    if phase:
        print(exchange_header(persona=phase.upper()))
    else:
        print(exchange_header())

    print(f"  {format_user(user_msg)}")

    # Show tool result when no chat response (tool-only mode)
    if not assistant_text and state and state.toolcall_status:
        print(f"  {format_assistant(_format_tool_result(state))}")
    else:
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

        session_id: str | None = None
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
                _print_transaction_result(phase_label, user_msg, assistant_text, metrics, state)
        finally:
            if session_id:
                await send_client_end(ws, session_id)


__all__ = ["run_once"]
