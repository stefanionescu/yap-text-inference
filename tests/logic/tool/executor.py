"""WebSocket execution utilities for tool regression tests.

This module provides the core execution logic for running tool test cases over
WebSocket connections. It handles connection management, message sending,
and result collection with configurable concurrency.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from collections.abc import Callable, Sequence

import websockets  # type: ignore[import-not-found]

from tests.config import (
    POST_TOOL_IDLE_MIN_S,
    TOOL_WS_MESSAGE_WINDOW_SECONDS,
    TOOL_WS_MAX_MESSAGES_PER_WINDOW,
)
from tests.helpers.metrics import secs_to_ms
from tests.helpers.rate import SlidingWindowPacer
from tests.helpers.websocket import connect_with_retries, send_client_end

from .cases import render_history
from .drain import DrainConfig, drain_response
from .types import (
    CaseResult,
    CaseStep,
    FailureRecord,
    RunnerConfig,
    StepTiming,
    ToolTestCase,
    TurnResult,
)
from .validation import derive_tool_called_from_raw, format_bool, is_valid_response_shape

STEP_WINDOW_SECONDS = max(0.0, float(TOOL_WS_MESSAGE_WINDOW_SECONDS))
STEP_MAX_PER_WINDOW = max(0, int(TOOL_WS_MAX_MESSAGES_PER_WINDOW))


async def _run_user_turn(
    ws,
    payload: dict[str, Any],
    timeout_s: float,
) -> TurnResult:
    """Send a user message and drain the response."""
    await ws.send(json.dumps(payload))
    cfg = DrainConfig(
        timeout_s=timeout_s,
        chat_idle_timeout_s=max(timeout_s, POST_TOOL_IDLE_MIN_S),
    )
    return await drain_response(ws, cfg)


def _coerce_missing_tool_result(turn: TurnResult, expected: bool | None) -> TurnResult:
    """Coerce missing tool response to success when expecting no tool call.
    
    Some setups avoid tool-calling altogether, so the server never emits a
    toolcall frame. For cases that explicitly expect no tool call, treat
    the absence of tool output as the desired outcome.
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


async def _execute_case(
    ws,
    session_id: str,
    case: ToolTestCase,
    cfg: RunnerConfig,
) -> CaseResult:
    """Execute a single test case over an open WebSocket connection."""
    history: list[CaseStep] = []
    turn_raws: list[Any] = []
    step_timings: list[StepTiming] = []
    failures: list[FailureRecord] = []
    step_pacer = SlidingWindowPacer(STEP_MAX_PER_WINDOW, STEP_WINDOW_SECONDS)

    for step_idx, step in enumerate(case.steps, start=1):
        result = await _execute_step(
            ws, cfg, session_id, step, step_idx, history, step_pacer
        )
        history.append(step)
        turn_raws.append(result.tool_raw)
        step_timings.append(
            StepTiming(
                step_index=step_idx,
                ttfb_ms=secs_to_ms(result.ttfb_s),
                total_ms=secs_to_ms(result.total_s),
            )
        )

        failure = _check_step_result(result, step, step_idx)
        if failure:
            failures.append(failure)

    return _build_case_result(case, failures, turn_raws, step_timings)


async def _execute_step(
    ws,
    cfg: RunnerConfig,
    session_id: str,
    step: CaseStep,
    step_idx: int,
    history: list[CaseStep],
    step_pacer: SlidingWindowPacer,
) -> TurnResult:
    """Execute a single step within a test case."""
    payload = _build_step_payload(cfg, session_id, step.text, history)
    await step_pacer.wait_turn()
    turn = await _run_user_turn(ws, payload, timeout_s=cfg.timeout_s)
    return _coerce_missing_tool_result(turn, step.expect_tool)


def _build_step_payload(
    cfg: RunnerConfig,
    session_id: str,
    user_text: str,
    history: list[CaseStep],
) -> dict[str, Any]:
    """Build the start message payload for a step.
    
    Note: chat_prompt is required by the server when DEPLOY_CHAT is enabled.
    """
    if not cfg.chat_prompt:
        raise ValueError(
            "chat_prompt is required for tool tests. "
            "Use select_chat_prompt(gender) to get a valid prompt."
        )
    
    return {
        "type": "start",
        "session_id": session_id,
        "gender": cfg.gender,
        "personality": cfg.personality,
        "chat_prompt": cfg.chat_prompt,
        "history": render_history(history),
        "user_utterance": user_text,
    }


def _check_step_result(
    turn: TurnResult,
    step: CaseStep,
    step_idx: int,
) -> FailureRecord | None:
    """Check if a step result indicates a failure."""
    expected = step.expect_tool

    if not turn.ok:
        return FailureRecord(
            reason=turn.reason or "unknown",
            detail=f"step {step_idx}: {turn.detail or turn.reason}",
            failing_step=step_idx,
            expected=expected,
            actual=turn.tool_called,
        )

    if not is_valid_response_shape(turn):
        return FailureRecord(
            reason="wrong_format",
            detail=f"step {step_idx}: invalid tool response format (raw={turn.tool_raw!r})",
            failing_step=step_idx,
            expected=expected,
            actual=turn.tool_called,
        )

    # Correct tool_called based on parsed result
    actual = derive_tool_called_from_raw(turn.tool_raw)
    if actual is None:
        actual = turn.tool_called

    if expected is not None and actual != expected:
        return FailureRecord(
            reason="wrong_response",
            detail=(
                f"step {step_idx}: expected {format_bool(expected)} but "
                f"got {format_bool(actual)} (raw={turn.tool_raw!r})"
            ),
            failing_step=step_idx,
            expected=expected,
            actual=actual,
        )

    return None


def _build_case_result(
    case: ToolTestCase,
    failures: list[FailureRecord],
    turn_raws: list[Any],
    step_timings: list[StepTiming],
) -> CaseResult:
    """Build the final case result from accumulated data."""
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
    return CaseResult(
        case=case,
        success=True,
        responses=list(turn_raws),
        step_timings=list(step_timings),
    )


async def _run_case(case: ToolTestCase, cfg: RunnerConfig) -> CaseResult:
    """Run a single test case with connection management."""
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
        return CaseResult(
            case=case,
            success=False,
            reason="connection_failed",
            detail=str(exc),
        )


async def run_all_cases(
    cases: Sequence[ToolTestCase],
    cfg: RunnerConfig,
    concurrency: int,
    *,
    progress_cb: Callable[[int, int], None] | None = None,
) -> list[CaseResult]:
    """Run all test cases with bounded concurrency.
    
    Args:
        cases: Sequence of test cases to run.
        cfg: Runner configuration.
        concurrency: Maximum concurrent test cases.
        progress_cb: Optional callback for progress updates.
    
    Returns:
        List of case results in original order.
    """
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


__all__ = ["run_all_cases"]
