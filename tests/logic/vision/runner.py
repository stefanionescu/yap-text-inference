"""Vision test runner for toolcall → followup flow.

This module provides the run_once function that tests the complete vision
flow: initial request triggering a toolcall YES, followed by a followup
message with analysis text. Reports timing metrics for both phases.
"""

from __future__ import annotations

import json
import uuid

import websockets

from tests.config import DEFAULT_GENDER, DEFAULT_PERSONALITY, DEFAULT_WS_PING_INTERVAL, DEFAULT_WS_PING_TIMEOUT
from tests.helpers.fmt import (
    dim,
    exchange_footer,
    exchange_header,
    format_assistant,
    format_metrics_inline,
    format_user,
    green,
    red,
    section_header,
    yellow,
)
from tests.helpers.websocket import (
    build_envelope,
    build_start_payload,
    create_tracker,
    finalize_metrics,
    iter_messages,
    record_token,
    record_toolcall,
    send_client_end,
    with_api_key,
)
from tests.messages.vision import SCREEN_ANALYSIS_TEXT, SCREEN_ANALYSIS_USER_REPLY
from tests.state import SessionContext, StreamState

# ============================================================================
# Internal Helpers
# ============================================================================


async def _consume_initial_response(ws, state: StreamState) -> tuple[bool, str]:
    """Consume initial response, tracking if toolcall YES was received."""
    saw_tool_yes = False
    async for msg in iter_messages(ws):
        t = msg.get("type")

        if t == "ack":
            state.ack_seen = True
            continue
        if t == "toolcall":
            status = (msg.get("status") or "").lower()
            record_toolcall(state)
            if status == "yes":
                saw_tool_yes = True
                print(f"  {green('TOOLCALL')} status=YES")
            else:
                print(f"  {yellow('TOOLCALL')} status={status.upper()}")
            continue
        if t == "token":
            record_token(state, msg.get("text", ""))
            continue
        if t == "final":
            if msg.get("normalized_text"):
                state.final_text = msg["normalized_text"]
            continue
        if t == "done":
            break
        if t == "error":
            raise RuntimeError(msg)
    return saw_tool_yes, state.final_text


async def _consume_followup(ws, state: StreamState) -> str:
    """Consume followup response."""
    async for msg in iter_messages(ws):
        t = msg.get("type")
        if t == "token":
            record_token(state, msg.get("text", ""))
            continue
        if t == "final":
            if msg.get("normalized_text"):
                state.final_text = msg["normalized_text"]
            continue
        if t == "done":
            break
        if t == "error":
            raise RuntimeError(msg)
    return state.final_text


# ============================================================================
# Public API
# ============================================================================


async def run_once(
    server: str,
    api_key: str | None,
    sampling: dict[str, float | int] | None,
    chat_prompt: str,
) -> None:
    """Execute the vision flow test."""
    ws_url = with_api_key(server, api_key=api_key)
    session_id = str(uuid.uuid4())
    ctx = SessionContext(
        session_id=session_id,
        gender=DEFAULT_GENDER,
        personality=DEFAULT_PERSONALITY,
        chat_prompt=chat_prompt,
        sampling=sampling,
    )
    start_payload = build_start_payload(ctx, SCREEN_ANALYSIS_USER_REPLY)

    print(f"\n{section_header('VISION TEST')}")
    print(dim(f"  server: {server}"))
    print(dim(f"  persona: {DEFAULT_PERSONALITY}/{DEFAULT_GENDER}\n"))

    async with websockets.connect(
        ws_url,
        max_queue=None,
        ping_interval=DEFAULT_WS_PING_INTERVAL,
        ping_timeout=DEFAULT_WS_PING_TIMEOUT,
    ) as ws:
        try:
            # Phase 1: Initial request (should trigger toolcall YES)
            print(exchange_header(idx=1, persona="INITIAL"))
            print(f"  {format_user(SCREEN_ANALYSIS_USER_REPLY)}")

            state1 = create_tracker()
            await ws.send(json.dumps(start_payload))
            saw_tool_yes, short_text = await _consume_initial_response(ws, state1)
            metrics1 = finalize_metrics(state1)

            print(f"  {format_assistant(short_text)}")
            print(f"  {format_metrics_inline(metrics1)}")
            print(exchange_footer())

            if not saw_tool_yes:
                print(f"\n  {red('FAIL')} Did not receive toolcall 'yes'")
                raise RuntimeError("Did not receive toolcall 'yes'")

            # Phase 2: Followup with analysis text
            print(exchange_header(idx=2, persona="FOLLOWUP"))
            print(f"  {dim('(sending vision text...)')}")

            followup_payload = build_envelope(
                "followup",
                session_id,
                f"req-{uuid.uuid4()}",
                {"analysis_text": SCREEN_ANALYSIS_TEXT},
            )
            state2 = create_tracker()
            await ws.send(json.dumps(followup_payload))
            final_followup = await _consume_followup(ws, state2)
            metrics2 = finalize_metrics(state2)

            print(f"  {format_assistant(final_followup)}")
            print(f"  {format_metrics_inline(metrics2)}")
            print(exchange_footer())

            print(f"\n  {green('✓ PASS')} Vision flow completed successfully")

        finally:
            await send_client_end(ws, session_id)


__all__ = ["run_once"]
