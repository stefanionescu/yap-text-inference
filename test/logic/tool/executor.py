"""Websocket execution utilities for tool regression tests."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, Sequence

import websockets  # type: ignore[import-not-found]

from common.message import iter_messages
from common.ws import connect_with_retries, send_client_end
from .cases import render_history
from .types import CaseResult, CaseStep, RunnerConfig, StepTiming, ToolTestCase, TurnResult

__all__ = ["run_all_cases"]


def _tool_status_to_bool(status: str | None) -> bool | None:
    if status is None:
        return None
    lowered = status.lower()
    if lowered == "yes":
        return True
    if lowered == "no":
        return False
    return None


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def _extract_json_array(text: str) -> list | None:
    """Try to extract a JSON array from text, handling trailing content."""
    if not isinstance(text, str):
        return None
    text = text.strip()
    if not text.startswith("["):
        return None
    
    # Try to find the closing bracket of the JSON array
    # This handles cases where there's extra text after the JSON
    bracket_count = 0
    in_string = False
    escape_next = False
    
    for i, char in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"' and not escape_next:
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "[":
            bracket_count += 1
        elif char == "]":
            bracket_count -= 1
            if bracket_count == 0:
                # Found the end of the JSON array
                try:
                    parsed = json.loads(text[:i + 1])
                    if isinstance(parsed, list):
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    pass
                return None
    return None


def _is_valid_response_shape(turn: TurnResult) -> bool:
    """Validate tool response shape, handling up to 25 tokens with possible trailing content."""
    raw = turn.tool_raw
    
    if turn.tool_called:
        # Tool was called - expect a non-empty list with tool call dicts
        parsed_list = None
        
        if isinstance(raw, list):
            parsed_list = raw
        elif isinstance(raw, str):
            # Try to extract JSON array from string (handles trailing content)
            parsed_list = _extract_json_array(raw)
        
        if not parsed_list or len(parsed_list) == 0:
            return False
        
        # Validate each item in the list
        for item in parsed_list:
            if not isinstance(item, dict):
                return False
            if "name" not in item:
                return False
            # "arguments" is optional but if present should be a dict
            if "arguments" in item and not isinstance(item["arguments"], dict):
                return False
        
        return True
    
    # Tool was not called - expect empty list, None, or empty string/array
    if raw is None:
        return True
    
    if isinstance(raw, list):
        return len(raw) == 0
    
    if isinstance(raw, str):
        # Try to parse as JSON array - should be empty
        parsed = _extract_json_array(raw)
        if parsed is not None:
            return len(parsed) == 0
        # If it's a string that doesn't parse as JSON array, check if it's empty or "[]"
        stripped = raw.strip()
        return stripped == "" or stripped == "[]"
    
    return False


def _secs_to_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1000.0


async def _drain_response(ws, *, timeout_s: float, start_ts: float) -> TurnResult:
    state: dict[str, Any] = {
        "tool_status": None,
        "tool_raw": None,
        "chat_seen": False,
        "done": False,
        "cancelled": False,
        "error": None,
    }
    first_frame_s: float | None = None

    async def _consume() -> None:
        nonlocal first_frame_s
        async for msg in iter_messages(ws):
            msg_type = msg.get("type")
            if msg_type == "ack":
                continue
            if first_frame_s is None:
                first_frame_s = time.perf_counter() - start_ts
            if msg_type == "toolcall":
                state["tool_status"] = str(msg.get("status") or "").strip().lower()
                state["tool_raw"] = msg.get("raw")
                continue
            if msg_type in {"token", "final"}:
                state["chat_seen"] = True
                continue
            if msg_type == "done":
                state["done"] = True
                state["cancelled"] = bool(msg.get("cancelled"))
                return
            if msg_type == "error":
                state["error"] = msg
                return

    try:
        await asyncio.wait_for(_consume(), timeout=timeout_s)
    except asyncio.TimeoutError:
        total_elapsed = time.perf_counter() - start_ts
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="timeout",
            detail=f"no response within {timeout_s:.1f}s",
            ttfb_s=first_frame_s,
            total_s=total_elapsed,
        )

    total_elapsed = time.perf_counter() - start_ts
    if state["error"]:
        detail = json.dumps(state["error"], ensure_ascii=False)
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=None,
            tool_raw=None,
            chat_seen=state["chat_seen"],
            reason="server_error",
            detail=detail,
            ttfb_s=first_frame_s,
            total_s=total_elapsed,
        )

    if not state["done"]:
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="incomplete",
            detail="stream ended before 'done'",
            ttfb_s=first_frame_s,
            total_s=total_elapsed,
        )

    if state["cancelled"]:
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="cancelled",
            detail="server reported cancellation",
            ttfb_s=first_frame_s,
            total_s=total_elapsed,
        )

    tool_bool = _tool_status_to_bool(state["tool_status"])
    if tool_bool is None:
        if state["tool_status"] is None:
            reason = "chat_only" if state["chat_seen"] else "no_tool_response"
            detail = "received chat output but no toolcall" if state["chat_seen"] else "no frames received"
            return TurnResult(
                ok=False,
                tool_called=None,
                tool_status=None,
                tool_raw=state["tool_raw"],
                chat_seen=state["chat_seen"],
                reason=reason,
                detail=detail,
                ttfb_s=first_frame_s,
                total_s=total_elapsed,
            )
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="invalid_tool_status",
            detail=f"toolcall status '{state['tool_status']}' is not yes/no",
            ttfb_s=first_frame_s,
            total_s=total_elapsed,
        )

    return TurnResult(
        ok=True,
        tool_called=tool_bool,
        tool_status=state["tool_status"],
        tool_raw=state["tool_raw"],
        chat_seen=state["chat_seen"],
        ttfb_s=first_frame_s,
        total_s=total_elapsed,
    )


async def _run_user_turn(
    ws,
    payload: dict[str, Any],
    timeout_s: float,
) -> TurnResult:
    await ws.send(json.dumps(payload))
    start_ts = time.perf_counter()
    return await _drain_response(ws, timeout_s=timeout_s, start_ts=start_ts)


async def _execute_case(ws, session_id: str, case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    history: list[CaseStep] = []
    user_turn_index = 0
    turn_raws: list[Any] = []
    step_timings: list[StepTiming] = []

    for step in case.steps:
        user_turn_index += 1
        history_text = render_history(history)
        payload = {
            "type": "start",
            "session_id": session_id,
            "gender": cfg.gender,
            "personality": cfg.personality,
            "chat_prompt": cfg.chat_prompt,
            "history_text": history_text,
            "user_utterance": step.text,
            "tool_prompt": cfg.tool_prompt,
        }

        turn = await _run_user_turn(ws, payload, timeout_s=cfg.timeout_s)
        history.append(step)
        turn_raws.append(turn.tool_raw)
        step_timings.append(
            StepTiming(
                step_index=user_turn_index,
                ttfb_ms=_secs_to_ms(turn.ttfb_s),
                total_ms=_secs_to_ms(turn.total_s),
            )
        )

        if not turn.ok:
            detail = f"step {user_turn_index}: {turn.detail or turn.reason}"
            return CaseResult(
                case=case,
                success=False,
                reason=turn.reason or "unknown",
                detail=detail,
                failing_step=user_turn_index,
                expected=step.expect_tool,
                actual=turn.tool_called,
                responses=list(turn_raws),
                step_timings=list(step_timings),
            )

        if not _is_valid_response_shape(turn):
            detail = f"step {user_turn_index}: invalid tool response format (raw={turn.tool_raw!r})"
            return CaseResult(
                case=case,
                success=False,
                reason="wrong_format",
                detail=detail,
                failing_step=user_turn_index,
                expected=step.expect_tool,
                actual=turn.tool_called,
                responses=list(turn_raws),
                step_timings=list(step_timings),
            )

        actual = turn.tool_called
        expected = step.expect_tool
        if expected is None:
            continue
        if actual != expected:
            detail = (
                f"step {user_turn_index}: expected {_format_bool(expected)} but "
                f"got {_format_bool(actual)} (raw={turn.tool_raw!r})"
            )
            return CaseResult(
                case=case,
                success=False,
                reason="wrong_response",
                detail=detail,
                failing_step=user_turn_index,
                expected=expected,
                actual=actual,
                responses=list(turn_raws),
                step_timings=list(step_timings),
            )

    return CaseResult(case=case, success=True, responses=list(turn_raws), step_timings=list(step_timings))


async def _run_case(case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    session_id = f"tooltest-{uuid.uuid4()}"
    try:
        async with connect_with_retries(
            lambda: websockets.connect(
                cfg.ws_url,
                max_queue=None,
                ping_interval=cfg.ping_interval,
                ping_timeout=cfg.ping_timeout,
            )
        ) as ws:
            try:
                return await _execute_case(ws, session_id, case, cfg)
            finally:
                await send_client_end(ws)
    except Exception as exc:  # noqa: BLE001
        return CaseResult(case=case, success=False, reason="connection_failed", detail=str(exc))


async def run_all_cases(
    cases: Sequence[ToolTestCase],
    cfg: RunnerConfig,
    concurrency: int,
) -> list[CaseResult]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def _bounded(case: ToolTestCase) -> CaseResult:
        async with semaphore:
            return await _run_case(case, cfg)

    tasks = [asyncio.create_task(_bounded(case)) for case in cases]
    return await asyncio.gather(*tasks)

