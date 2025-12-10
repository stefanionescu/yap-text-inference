from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

from tests.helpers.message import iter_messages
from tests.helpers.prompt import (
    PROMPT_MODE_BOTH,
    select_chat_prompt,
    select_tool_prompt,
    should_send_chat_prompt,
    should_send_tool_prompt,
)
from tests.helpers.regex import contains_complete_sentence, has_at_least_n_words
from tests.helpers.util import choose_message
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from .reporting import print_report

# Ensure prompts/config modules are importable when running as script
_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

from tests.config import BENCHMARK_FALLBACK_MESSAGE, CLASSIFIER_MODE  # noqa: E402


@dataclass
class _StreamTracker:
    """Track benchmark timing metrics as messages stream in."""

    t_sent: float = field(default_factory=time.perf_counter)
    final_text: str = ""
    ttfb_toolcall_ms: float | None = None
    ttfb_chat_ms: float | None = None
    first_sentence_ms: float | None = None
    first_3_words_ms: float | None = None

    def _elapsed_ms(self) -> float:
        return (time.perf_counter() - self.t_sent) * 1000.0

    def record_toolcall(self) -> None:
        if self.ttfb_toolcall_ms is None:
            self.ttfb_toolcall_ms = self._elapsed_ms()

    def record_token(self, chunk: str) -> None:
        if not chunk:
            return
        if self.ttfb_chat_ms is None:
            self.ttfb_chat_ms = self._elapsed_ms()
        self.final_text += chunk
        if self.first_3_words_ms is None and has_at_least_n_words(self.final_text, 3):
            self.first_3_words_ms = self._elapsed_ms()
        if self.first_sentence_ms is None and contains_complete_sentence(self.final_text):
            self.first_sentence_ms = self._elapsed_ms()

    def apply_normalized_text(self, normalized: str | None) -> None:
        if normalized:
            self.final_text = normalized

    def build_result(self, cancelled: bool) -> dict[str, Any]:
        return {
            "ok": not cancelled,
            "ttfb_toolcall_ms": self.ttfb_toolcall_ms,
            "ttfb_chat_ms": self.ttfb_chat_ms,
            "first_sentence_ms": self.first_sentence_ms,
            "first_3_words_ms": self.first_3_words_ms,
        }


def _build_start_payload(
    session_id: str,
    gender: str,
    style: str,
    chat_prompt: str | None,
    tool_prompt: str | None,
    message: str,
    sampling: dict[str, float | int] | None,
    *,
    classifier_mode: bool = False,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": style,
        "history_text": "",
        "user_utterance": message,
    }
    if chat_prompt is not None:
        payload["chat_prompt"] = chat_prompt
    if tool_prompt is not None:
        payload["tool_prompt"] = tool_prompt
    # In classifier mode, tool_prompt is not required
    if not classifier_mode and "chat_prompt" not in payload and "tool_prompt" not in payload:
        raise ValueError("prompt_mode must include chat, tool, or both prompts")
    if sampling:
        payload["sampling"] = sampling
    return payload


async def _consume_stream(ws, tracker: _StreamTracker) -> dict[str, Any]:
    async for msg in iter_messages(ws):
        msg_type = msg.get("type")

        if msg_type == "toolcall":
            tracker.record_toolcall()
            continue

        if msg_type == "token":
            tracker.record_token(msg.get("text", ""))
            continue

        if msg_type == "final":
            tracker.apply_normalized_text(msg.get("normalized_text"))
            continue

        if msg_type == "done":
            cancelled = bool(msg.get("cancelled"))
            return tracker.build_result(cancelled)

        if msg_type == "error":
            return _error_from_message(msg)

    return {"ok": False, "error": "stream ended before 'done'"}


def _error_from_message(msg: dict[str, Any]) -> dict[str, Any]:
    error_code = msg.get("error_code", "")
    error_message = msg.get("message", "unknown error")
    if error_code:
        return {"ok": False, "error": f"{error_code}: {error_message}"}
    return {"ok": False, "error": error_message}


async def _one_connection(
    url: str,
    api_key: str | None,
    gender: str,
    style: str,
    chat_prompt: str | None,
    tool_prompt: str | None,
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
    classifier_mode: bool = False,
) -> list[dict[str, Any]]:
    phases = 2 if double_ttfb else 1
    results: list[dict[str, Any]] = []

    async def _session() -> None:
        auth_url = with_api_key(url, api_key=api_key)
        async with connect_with_retries(lambda: websockets.connect(auth_url, max_queue=None)) as ws:
            try:
                for phase in range(1, phases + 1):
                    try:
                        results.append(
                            await _send_transaction(
                                ws,
                                gender,
                                style,
                                chat_prompt,
                                tool_prompt,
                                message,
                                sampling,
                                phase,
                                classifier_mode=classifier_mode,
                            )
                        )
                    except Exception as phase_err:
                        results.append({"ok": False, "error": str(phase_err), "phase": phase})
                        break
            finally:
                await send_client_end(ws)

    try:
        await asyncio.wait_for(_session(), timeout=timeout_s)
    except Exception as e:
        if len(results) < phases:
            results.append({"ok": False, "error": str(e), "phase": len(results) + 1})
    return results


async def _send_transaction(
    ws,
    gender: str,
    style: str,
    chat_prompt: str | None,
    tool_prompt: str | None,
    message: str,
    sampling: dict[str, float | int] | None,
    phase: int,
    *,
    classifier_mode: bool = False,
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    start_payload = _build_start_payload(
        session_id,
        gender,
        style,
        chat_prompt,
        tool_prompt,
        message,
        sampling,
        classifier_mode=classifier_mode,
    )
    tracker = _StreamTracker()

    await ws.send(json.dumps(start_payload))
    result = await _consume_stream(ws, tracker)
    result["phase"] = phase
    return result


async def _worker(
    num: int,
    url: str,
    api_key: str | None,
    gender: str,
    style: str,
    chat_prompt: str | None,
    tool_prompt: str | None,
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
    classifier_mode: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for _ in range(num):
        out.extend(
            await _one_connection(
                url,
                api_key,
                gender,
                style,
                chat_prompt,
                tool_prompt,
                message,
                timeout_s,
                sampling,
                double_ttfb,
                classifier_mode,
            )
        )
    return out


async def run_benchmark(args) -> None:
    (
        url,
        api_key,
        gender,
        style,
        message,
        sampling,
    ) = _extract_session_options(args)
    requests, concurrency = _sanitize_workload_args(int(args.requests), int(args.concurrency))
    counts = _distribute_requests(requests, concurrency)
    timeout_s = float(args.timeout)
    prompt_mode = getattr(args, "prompt_mode", PROMPT_MODE_BOTH)
    classifier_mode = getattr(args, "classifier_mode", CLASSIFIER_MODE)
    chat_prompt = select_chat_prompt(gender) if should_send_chat_prompt(prompt_mode) else None
    tool_prompt = select_tool_prompt() if should_send_tool_prompt(prompt_mode, classifier_mode=classifier_mode) else None
    double_ttfb = bool(getattr(args, "double_ttfb", False))

    tasks = _launch_worker_tasks(
        counts,
        url,
        api_key,
        gender,
        style,
        chat_prompt,
        tool_prompt,
        message,
        timeout_s,
        sampling,
        double_ttfb,
        classifier_mode,
    )
    nested = await asyncio.gather(*tasks)
    results: list[dict[str, Any]] = [item for sub in nested for item in sub]

    print_report(url, requests, concurrency, results, double_ttfb=double_ttfb)


def _extract_session_options(
    args,
) -> tuple[str, str | None, str, str, str, dict[str, float | int] | None]:
    message = choose_message(args.message, fallback=BENCHMARK_FALLBACK_MESSAGE)
    sampling = getattr(args, "sampling", None) or None
    return args.server, args.api_key, args.gender, args.personality, message, sampling


def _sanitize_workload_args(requests: int, concurrency: int) -> tuple[int, int]:
    safe_requests = max(1, requests)
    safe_concurrency = max(1, min(concurrency, safe_requests))
    return safe_requests, safe_concurrency


def _distribute_requests(requests: int, concurrency: int) -> list[int]:
    base, rem = divmod(requests, concurrency)
    return [base + (1 if i < rem else 0) for i in range(concurrency)]


def _launch_worker_tasks(
    counts: list[int],
    url: str,
    api_key: str | None,
    gender: str,
    style: str,
    chat_prompt: str | None,
    tool_prompt: str | None,
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
    classifier_mode: bool = False,
) -> list[asyncio.Task[list[dict[str, Any]]]]:
    tasks: list[asyncio.Task[list[dict[str, Any]]]] = []
    for count in counts:
        if count <= 0:
            continue
        tasks.append(
            asyncio.create_task(
                _worker(
                    count,
                    url,
                    api_key,
                    gender,
                    style,
                    chat_prompt,
                    tool_prompt,
                    message,
                    timeout_s,
                    sampling,
                    double_ttfb,
                    classifier_mode,
                )
            )
        )
    return tasks


