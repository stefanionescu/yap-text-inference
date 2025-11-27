"""Websocket execution utilities for tool regression tests."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Sequence

import websockets  # type: ignore[import-not-found]

from common.message import iter_messages
from common.ws import send_client_end
from prompts.toolcall import TOOLCALL_PROMPT

from .cases import render_history
from .types import CaseResult, CaseStep, RunnerConfig, ToolTestCase, TurnResult

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


async def _drain_response(ws, *, timeout_s: float) -> TurnResult:
    state: dict[str, Any] = {
        "tool_status": None,
        "tool_raw": None,
        "chat_seen": False,
        "done": False,
        "cancelled": False,
        "error": None,
    }

    async def _consume() -> None:
        async for msg in iter_messages(ws):
            msg_type = msg.get("type")
            if msg_type == "ack":
                continue
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
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="timeout",
            detail=f"no response within {timeout_s:.1f}s",
        )

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
            )
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="invalid_tool_status",
            detail=f"toolcall status '{state['tool_status']}' is not yes/no",
        )

    return TurnResult(
        ok=True,
        tool_called=tool_bool,
        tool_status=state["tool_status"],
        tool_raw=state["tool_raw"],
        chat_seen=state["chat_seen"],
    )


async def _run_user_turn(
    ws,
    payload: dict[str, Any],
    timeout_s: float,
) -> TurnResult:
    await ws.send(json.dumps(payload))
    return await _drain_response(ws, timeout_s=timeout_s)


async def _execute_case(ws, session_id: str, case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    history: list[CaseStep] = []
    user_turn_index = 0
    turn_raws: list[Any] = []

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
            "tool_prompt": TOOLCALL_PROMPT,
        }

        turn = await _run_user_turn(ws, payload, timeout_s=cfg.timeout_s)
        history.append(step)
        turn_raws.append(turn.tool_raw)

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
            )

    return CaseResult(case=case, success=True, responses=list(turn_raws))


async def _run_case(case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    session_id = f"tooltest-{uuid.uuid4()}"
    try:
        async with websockets.connect(
            cfg.ws_url,
            max_queue=None,
            ping_interval=cfg.ping_interval,
            ping_timeout=cfg.ping_timeout,
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

