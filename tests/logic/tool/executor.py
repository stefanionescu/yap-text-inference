"""Websocket execution utilities for tool regression tests."""

from __future__ import annotations

import asyncio
import inspect
import json
import time
import uuid
from typing import Any, Callable, Sequence

import websockets  # type: ignore[import-not-found]

from tests.config import POST_TOOL_IDLE_MIN_S
from tests.helpers.message import iter_messages
from tests.helpers.ws import connect_with_retries, send_client_end
from .cases import render_history
from .types import (
    CaseResult,
    CaseStep,
    FailureRecord,
    RunnerConfig,
    StepTiming,
    ToolTestCase,
    TurnResult,
)

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


def _derive_tool_called_from_raw(raw: Any) -> bool | None:
    """Derive tool_called boolean from raw response by parsing it.
    
    Returns True if non-empty array, False if empty array, None if can't parse.
    """
    parsed_list = None
    if raw is None:
        return None
    elif isinstance(raw, list):
        parsed_list = raw
    elif isinstance(raw, str):
        normalized = raw.strip()
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, list):
                parsed_list = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    
    if parsed_list is None:
        return None
    return len(parsed_list) > 0


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"




def _is_valid_response_shape(turn: TurnResult) -> bool:
    """Validate tool response shape.
    
    Expects a JSON array response.
    """
    raw = turn.tool_raw
    
    # Parse the JSON array from the raw response
    parsed_list = None
    if raw is None:
        # None is valid (means no response) - treat as empty array
        parsed_list = []
    elif isinstance(raw, list):
        parsed_list = raw
    elif isinstance(raw, str):
        normalized = raw.strip()
        try:
            parsed = json.loads(normalized)
            if isinstance(parsed, list):
                parsed_list = parsed
        except (json.JSONDecodeError, ValueError):
            pass
    
    # If we couldn't parse, it's invalid
    if parsed_list is None:
        return False
    
    # Validate format based on parsed result
    if len(parsed_list) > 0:
        # Tool was called - validate each item in the list has correct structure
        for item in parsed_list:
            if not isinstance(item, dict):
                return False
            if "name" not in item:
                return False
            # "arguments" is optional but if present should be a dict
            if "arguments" in item and not isinstance(item["arguments"], dict):
                return False
    
    return True


def _secs_to_ms(value: float | None) -> float | None:
    if value is None:
        return None
    return value * 1000.0


async def _close_connection(ws, *, reason: str | None = None) -> None:
    """Attempt to close the websocket connection gracefully."""
    close = getattr(ws, "close", None)
    if close is None:
        return
    try:
        if reason is None:
            result = close()
        else:
            try:
                result = close(reason=reason)
            except TypeError:
                result = close()
        if inspect.isawaitable(result):
            await result
    except Exception:
        # Best-effort close; ignore failures
        return


async def _drain_response(
    ws,
    *,
    timeout_s: float,
    chat_idle_timeout_s: float | None,
    start_ts: float,
) -> TurnResult:
    """
    Drain websocket frames until the server finishes the turn.

    The timeout applies only to the TOOL response (i.e., until we receive a
    ``toolcall`` frame). Once the tool decision arrives we continue waiting for
    the chat stream to flush without enforcing the per-turn timeout so that
    chat completions do not register as premature failures.
    """

    state: dict[str, Any] = {
        "tool_status": None,
        "tool_raw": None,
        "chat_seen": False,
        "done": False,
        "cancelled": False,
        "error": None,
    }
    first_tool_frame_s: float | None = None
    last_tool_frame_s: float | None = None
    tool_decision_received = False
    messages = iter_messages(ws)
    tool_deadline = start_ts + timeout_s

    while True:
        wait_timeout: float | None = None
        if not tool_decision_received:
            now = time.perf_counter()
            remaining = tool_deadline - now
            if remaining <= 0:
                await _close_connection(ws, reason="tool_timeout")
                return TurnResult(
                    ok=False,
                    tool_called=None,
                    tool_status=state["tool_status"],
                    tool_raw=state["tool_raw"],
                    chat_seen=state["chat_seen"],
                    reason="timeout",
                    detail=f"tool response not received within {timeout_s:.1f}s",
                    ttfb_s=first_tool_frame_s,
                    total_s=last_tool_frame_s,
                )
            wait_timeout = remaining
        elif chat_idle_timeout_s is not None:
            wait_timeout = chat_idle_timeout_s

        try:
            next_msg = messages.__anext__()
            msg = await (next_msg if wait_timeout is None else asyncio.wait_for(next_msg, wait_timeout))
        except asyncio.TimeoutError:
            await _close_connection(ws, reason="tool_timeout" if not tool_decision_received else "chat_idle_timeout")
            return TurnResult(
                ok=False,
                tool_called=None,
                tool_status=state["tool_status"],
                tool_raw=state["tool_raw"],
                chat_seen=state["chat_seen"],
                reason="timeout" if not tool_decision_received else "chat_timeout",
                detail=(
                    f"tool response not received within {timeout_s:.1f}s"
                    if not tool_decision_received
                    else f"no chat frames within {chat_idle_timeout_s:.1f}s after tool response"
                ),
                ttfb_s=first_tool_frame_s,
                total_s=last_tool_frame_s,
            )
        except StopAsyncIteration:
            break

        msg_type = msg.get("type")
        if msg_type == "ack":
            continue
        if msg_type == "toolcall":
            now = time.perf_counter()
            elapsed = now - start_ts
            if first_tool_frame_s is None:
                first_tool_frame_s = elapsed
            last_tool_frame_s = elapsed
            tool_decision_received = True
            state["tool_status"] = str(msg.get("status") or "").strip().lower()
            state["tool_raw"] = msg.get("raw")
            continue
        if msg_type in {"token", "final"}:
            state["chat_seen"] = True
            continue
        if msg_type == "done":
            state["done"] = True
            state["cancelled"] = bool(msg.get("cancelled"))
            break
        if msg_type == "error":
            state["error"] = msg
            break

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
            ttfb_s=first_tool_frame_s,
            total_s=last_tool_frame_s,
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
            ttfb_s=first_tool_frame_s,
            total_s=last_tool_frame_s,
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
            ttfb_s=first_tool_frame_s,
            total_s=last_tool_frame_s,
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
                ttfb_s=first_tool_frame_s,
                total_s=last_tool_frame_s,
            )
        return TurnResult(
            ok=False,
            tool_called=None,
            tool_status=state["tool_status"],
            tool_raw=state["tool_raw"],
            chat_seen=state["chat_seen"],
            reason="invalid_tool_status",
            detail=f"toolcall status '{state['tool_status']}' is not yes/no",
            ttfb_s=first_tool_frame_s,
            total_s=last_tool_frame_s,
        )

    return TurnResult(
        ok=True,
        tool_called=tool_bool,
        tool_status=state["tool_status"],
        tool_raw=state["tool_raw"],
        chat_seen=state["chat_seen"],
        ttfb_s=first_tool_frame_s,
        total_s=last_tool_frame_s,
    )


async def _run_user_turn(
    ws,
    payload: dict[str, Any],
    timeout_s: float,
) -> TurnResult:
    await ws.send(json.dumps(payload))
    start_ts = time.perf_counter()
    chat_idle_timeout_s = max(timeout_s, POST_TOOL_IDLE_MIN_S)
    return await _drain_response(
        ws,
        timeout_s=timeout_s,
        chat_idle_timeout_s=chat_idle_timeout_s,
        start_ts=start_ts,
    )


def _coerce_missing_tool_result(turn: TurnResult, expected: bool | None) -> TurnResult:
    """
    When a case explicitly expects no tool call, treat missing tool output as success.

    Some setups avoid tool-calling altogether, so the server never emits a
    ``toolcall`` frame. Historically we flagged that as a failure, but for these cases
    the absence of tool output is the desired outcome. Coerce such turns into a
    synthetic "no" decision so the rest of the pipeline treats them as successes.
    """

    if (
        expected is False
        and not turn.ok
        and turn.reason in {"no_tool_response", "chat_only"}
    ):
        return TurnResult(
            ok=True,
            tool_called=False,
            tool_status="no",
            tool_raw=turn.tool_raw if turn.tool_raw is not None else [],
            chat_seen=turn.chat_seen,
            ttfb_s=turn.ttfb_s,
            total_s=turn.total_s,
        )
    return turn


async def _execute_case(ws, session_id: str, case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    history: list[CaseStep] = []
    user_turn_index = 0
    turn_raws: list[Any] = []
    step_timings: list[StepTiming] = []
    failures: list[FailureRecord] = []

    def _record_failure(
        *,
        reason: str,
        detail: str,
        expected: bool | None,
        actual: bool | None,
        failing_step: int,
    ) -> None:
        failures.append(
            FailureRecord(
                reason=reason,
                detail=detail,
                failing_step=failing_step,
                expected=expected,
                actual=actual,
            )
        )

    for step in case.steps:
        user_turn_index += 1
        history_text = render_history(history)
        payload = {
            "type": "start",
            "session_id": session_id,
            "gender": cfg.gender,
            "personality": cfg.personality,
            "history_text": history_text,
            "user_utterance": step.text,
        }
        if cfg.chat_prompt is not None:
            payload["chat_prompt"] = cfg.chat_prompt

        turn = await _run_user_turn(ws, payload, timeout_s=cfg.timeout_s)
        expected = step.expect_tool
        turn = _coerce_missing_tool_result(turn, expected)
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
            _record_failure(
                reason=turn.reason or "unknown",
                detail=detail,
                expected=expected,
                actual=turn.tool_called,
                failing_step=user_turn_index,
            )
            continue

        if not _is_valid_response_shape(turn):
            detail = f"step {user_turn_index}: invalid tool response format (raw={turn.tool_raw!r})"
            _record_failure(
                reason="wrong_format",
                detail=detail,
                expected=step.expect_tool,
                actual=turn.tool_called,
                failing_step=user_turn_index,
            )
            continue

        # Correct tool_called based on parsed result (server status may be wrong with explanations)
        corrected_tool_called = _derive_tool_called_from_raw(turn.tool_raw)
        if corrected_tool_called is not None:
            # Override server's tool_called with parsed result
            actual = corrected_tool_called
        else:
            # Fallback to server's tool_called if we can't parse
            actual = turn.tool_called
        if expected is None:
            continue
        if actual != expected:
            detail = (
                f"step {user_turn_index}: expected {_format_bool(expected)} but "
                f"got {_format_bool(actual)} (raw={turn.tool_raw!r})"
            )
            _record_failure(
                reason="wrong_response",
                detail=detail,
                expected=expected,
                actual=actual,
                failing_step=user_turn_index,
            )
            continue

    if failures:
        first = failures[0]
        return CaseResult(
            case=case,
            success=False,
            reason=first.reason,
            detail=first.detail,
            failing_step=first.failing_step,
            expected=first.expected,
            actual=first.actual,
            responses=list(turn_raws),
            step_timings=list(step_timings),
            failures=list(failures),
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
    *,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[CaseResult]:
    case_list = list(cases)
    total = len(case_list)
    if total == 0:
        return []

    semaphore = asyncio.Semaphore(max(1, concurrency))
    if progress_cb:
        progress_cb(0, total)

    async def _run_bounded(index: int, case: ToolTestCase) -> tuple[int, CaseResult]:
        async with semaphore:
            result = await _run_case(case, cfg)
            return index, result

    tasks = [
        asyncio.create_task(_run_bounded(idx, case))
        for idx, case in enumerate(case_list)
    ]

    results: list[CaseResult | None] = [None] * total
    completed = 0
    for pending in asyncio.as_completed(tasks):
        idx, result = await pending
        results[idx] = result
        completed += 1
        if progress_cb:
            progress_cb(completed, total)

    return [r for r in results if r is not None]

