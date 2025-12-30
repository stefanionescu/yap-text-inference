from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass, field
from typing import Any

import websockets

from tests.helpers.message import iter_messages
from tests.helpers.prompt import select_chat_prompt
from tests.helpers.regex import contains_complete_sentence, has_at_least_n_words
from tests.helpers.util import choose_message
from tests.helpers.ws import connect_with_retries, send_client_end, with_api_key
from .reporting import print_report

# Ensure prompts/config modules are importable when running as script
_TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _TEST_DIR not in sys.path:
    sys.path.insert(0, _TEST_DIR)

import time

from tests.config import BENCHMARK_FALLBACK_MESSAGE, DEFAULT_PERSONALITIES  # noqa: E402


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
    message: str,
    sampling: dict[str, float | int] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "type": "start",
        "session_id": session_id,
        "gender": gender,
        "personality": style,
        "personalities": DEFAULT_PERSONALITIES,
        "history_text": "",
        "user_utterance": message,
    }
    if chat_prompt is not None:
        payload["chat_prompt"] = chat_prompt
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
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
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
                                message,
                                sampling,
                                phase,
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
    message: str,
    sampling: dict[str, float | int] | None,
    phase: int,
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    start_payload = _build_start_payload(
        session_id,
        gender,
        style,
        chat_prompt,
        message,
        sampling,
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
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
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
                message,
                timeout_s,
                sampling,
                double_ttfb,
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
    timeout_s = float(args.timeout)
    skip_chat_prompt = bool(getattr(args, "no_chat_prompt", False))
    chat_prompt = None if skip_chat_prompt else select_chat_prompt(gender)
    double_ttfb = bool(getattr(args, "double_ttfb", False))

    burst_mode = getattr(args, "burst_mode", "instant")
    burst_size = max(1, int(getattr(args, "burst_size", 3)))
    window_duration = float(getattr(args, "window_duration", 0.5))

    common_opts = (
        url,
        api_key,
        gender,
        style,
        chat_prompt,
        message,
        timeout_s,
        sampling,
        double_ttfb,
    )

    if burst_mode == "windowed":
        results = await _run_windowed_benchmark(
            requests, burst_size, window_duration, *common_opts
        )
    else:
        results = await _run_instant_benchmark(requests, concurrency, *common_opts)

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
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
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
                    message,
                    timeout_s,
                    sampling,
                    double_ttfb,
                )
            )
        )
    return tasks


async def _run_instant_benchmark(
    total_requests: int,
    concurrency: int,
    url: str,
    api_key: str | None,
    gender: str,
    style: str,
    chat_prompt: str | None,
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
) -> list[dict[str, Any]]:
    """
    Run benchmark in instant mode.

    Distributes all requests across `concurrency` workers and launches them
    simultaneously.
    """
    counts = _distribute_requests(total_requests, concurrency)
    tasks = _launch_worker_tasks(
        counts,
        url,
        api_key,
        gender,
        style,
        chat_prompt,
        message,
        timeout_s,
        sampling,
        double_ttfb,
    )
    nested = await asyncio.gather(*tasks)
    return [item for sub in nested for item in sub]


async def _run_windowed_benchmark(
    total_requests: int,
    burst_size: int,
    window_duration: float,
    url: str,
    api_key: str | None,
    gender: str,
    style: str,
    chat_prompt: str | None,
    message: str,
    timeout_s: float,
    sampling: dict[str, float | int] | None,
    double_ttfb: bool,
) -> list[dict[str, Any]]:
    """
    Run benchmark in windowed burst mode.

    Sends `burst_size` transactions concurrently, then waits `window_duration`
    seconds before sending the next burst. Repeats until all requests are sent.
    """
    results: list[dict[str, Any]] = []
    remaining = total_requests

    while remaining > 0:
        batch_size = min(burst_size, remaining)
        window_start = time.perf_counter()

        # Launch batch_size concurrent connections
        tasks = [
            asyncio.create_task(
                _one_connection(
                    url,
                    api_key,
                    gender,
                    style,
                    chat_prompt,
                    message,
                    timeout_s,
                    sampling,
                    double_ttfb,
                )
            )
            for _ in range(batch_size)
        ]

        # Wait for all tasks in this window to complete
        nested = await asyncio.gather(*tasks)
        for sub in nested:
            results.extend(sub)

        remaining -= batch_size

        # If there are more requests, wait for the remainder of the window
        if remaining > 0:
            elapsed = time.perf_counter() - window_start
            sleep_time = window_duration - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

    return results
