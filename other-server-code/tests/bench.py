#!/usr/bin/env python3
"""
WebSocket streaming benchmark for Orpheus TTS server.

Sends concurrent WS sessions that push text and receive PCM16 audio frames.
Reports wall, audio duration, TTFB, RTF, xRT, throughput.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import os
import sys
import time
from pathlib import Path

import websockets

# Ensure repository root is on sys.path so `server` package is importable
_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from server.text.prompts import chunk_by_sentences  # noqa: E402
from tests.utils.audio import leading_silence_ms  # noqa: E402
from tests.utils.common import (  # noqa: E402
    DEFAULT_SAMPLE_RATE,
    DEFAULT_TEXT,
    END_SENTINEL,
    build_meta,
    is_busy_error,
    load_texts,
    parse_bool,
    websocket_connect_kwargs,
    ws_tts_url,
)
from tests.utils.report import report_sentence_mismatch, summarize_bench  # noqa: E402
from tests.utils.stream import recv_pcm_and_sentences  # noqa: E402


async def _tts_one_ws(  # noqa: PLR0913
    server: str,
    text: str,
    voice: str,
    trim_silence: bool,
    temperature: float | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    prespeech_pad_ms: float | None = None,
    api_key: str | None = None,
) -> dict[str, float]:
    url = ws_tts_url(server)

    t0_e2e = time.perf_counter()
    t0_server: float | None = None
    sr = DEFAULT_SAMPLE_RATE

    sentences = [s for s in chunk_by_sentences(text) if s and s.strip()]
    connect_kwargs = websocket_connect_kwargs(api_key, max_size=None)

    async with websockets.connect(url, **connect_kwargs) as ws:
        await ws.send(
            json.dumps(build_meta(voice, trim_silence, temperature, top_p, repetition_penalty, prespeech_pad_ms))
        )

        recv_task = asyncio.create_task(recv_pcm_and_sentences(ws))

        for _idx, sentence in enumerate(sentences):
            await ws.send(json.dumps({"text": sentence.strip(), "voice": voice}))
            if t0_server is None:
                t0_server = time.perf_counter()

        await ws.send(END_SENTINEL)
        pcm_data, recv_sentences, first_chunk_at = await recv_task

    wall_s = time.perf_counter() - t0_e2e
    audio_s = (len(pcm_data) / 2.0) / float(sr) if pcm_data else 0.0
    ttfb_e2e_s = (first_chunk_at - t0_e2e) if first_chunk_at else 0.0
    ttfb_server_s = (first_chunk_at - t0_server) if (first_chunk_at and t0_server) else 0.0
    rtf = (wall_s / audio_s) if audio_s > 0 else float("inf")
    xrt = (audio_s / wall_s) if wall_s > 0 else 0.0
    lead_ms = float(leading_silence_ms(pcm_data, sr)) if pcm_data else 0.0

    if recv_sentences != sentences:
        report_sentence_mismatch("BENCH", sentences, recv_sentences)

    return {
        "wall_s": float(wall_s),
        "audio_s": float(audio_s),
        "ttfb_e2e_s": float(ttfb_e2e_s),
        "ttfb_server_s": float(ttfb_server_s),
        "rtf": float(rtf),
        "xrt": float(xrt),
        "throughput_min_per_min": float(xrt),
        "leading_silence_ms": lead_ms,
    }


def _summarize(title: str, results: list[dict[str, float]]) -> None:
    summarize_bench(title, results)


def _load_texts(inline_texts: list[str] | None) -> list[str]:
    return load_texts(inline_texts, DEFAULT_TEXT)


async def bench_ws(  # noqa: PLR0913
    server: str,
    total_reqs: int,
    concurrency: int,
    voice: str,
    texts: list[str],
    trim_silence: bool,
    temperature: float | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    prespeech_pad_ms: float | None = None,
    api_key: str | None = None,
) -> tuple[list[dict[str, float]], int, int]:
    sem = asyncio.Semaphore(max(1, concurrency))
    results: list[dict[str, float]] = []
    errors_total = 0
    busy_errors = 0

    async def worker(req_idx: int):
        nonlocal errors_total
        nonlocal busy_errors
        text = texts[req_idx % len(texts)]
        async with sem:
            try:
                r = await _tts_one_ws(
                    server,
                    text,
                    voice,
                    trim_silence,
                    temperature,
                    top_p,
                    repetition_penalty,
                    prespeech_pad_ms,
                    api_key,
                )
                results.append(r)
            except Exception as e:
                errors_total += 1
                if is_busy_error(e):
                    busy_errors += 1
                kind = "BUSY" if is_busy_error(e) else "ERROR"
                print(
                    f"[bench] {kind} idx={req_idx} err={e}",
                    file=sys.stderr,
                )

    tasks = [asyncio.create_task(worker(i)) for i in range(total_reqs)]
    await asyncio.gather(*tasks, return_exceptions=True)

    return results[:total_reqs], errors_total, busy_errors


def main() -> None:
    ap = argparse.ArgumentParser(description="WebSocket streaming benchmark (Orpheus TTS)")
    ap.add_argument("--server", default="127.0.0.1:8000", help="host:port or http[s]://host:port")
    ap.add_argument("--n", type=int, default=16, help="Total requests")
    ap.add_argument("--concurrency", type=int, default=16, help="Max concurrent sessions")
    ap.add_argument("--voice", type=str, default=os.environ.get("TTS_VOICE", "female"), help="Voice alias: female|male")
    ap.add_argument("--trim-silence", default="true", help="Trim leading silence on server (true|false)")
    ap.add_argument("--text", action="append", default=None, help="Inline text prompt (repeat for multiple)")
    ap.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Temperature for generation (0.3-0.9). If not specified, uses voice default",
    )
    ap.add_argument(
        "--top-p", type=float, default=None, help="Top-p for generation (0.7-1.0). If not specified, uses voice default"
    )
    ap.add_argument(
        "--repetition-penalty",
        type=float,
        default=None,
        help="Repetition penalty for generation (1.1-1.9). If not specified, uses voice default",
    )
    ap.add_argument("--api-key", default=os.environ.get("ORPHEUS_API_KEY"), help="API key (required)")
    ap.add_argument(
        "--prespeech-pad-ms",
        type=float,
        default=None,
        help="Pre-speech pad in ms when trimming (50-700). Omit to use server default",
    )
    args = ap.parse_args()
    texts = _load_texts(args.text)

    print(f"Benchmark → WebSocket stream | n={args.n} | concurrency={args.concurrency} | server={args.server}")
    print(f"Voice: {args.voice}")
    print(f"Texts: {len(texts)}")

    t0 = time.time()
    trim_flag = parse_bool(args.trim_silence)
    results, errors, busy_errors = asyncio.run(
        bench_ws(
            args.server,
            args.n,
            args.concurrency,
            args.voice,
            texts,
            trim_flag,
            args.temperature,
            getattr(args, "top_p", None),
            getattr(args, "repetition_penalty", None),
            getattr(args, "prespeech_pad_ms", None),
            args.api_key,
        )
    )
    elapsed = time.time() - t0

    _summarize("TTS Streaming", results)
    other_errors = max(0, errors - busy_errors)
    print(f"Errors: {errors} (busy={busy_errors}, other={other_errors})")

    # Optional validation if expected limit is provided via environment
    expected_limit: int | None = None
    with contextlib.suppress(Exception):
        env_lim = os.environ.get("WS_MAX_CONNECTIONS", "").strip()
        if env_lim.isdigit():
            expected_limit = int(env_lim)

    if expected_limit is not None:
        expected_busy = max(0, min(args.n, args.concurrency) - expected_limit)
        print(
            "Capacity limit check: "
            f"limit={expected_limit} | expected busy={expected_busy} | observed busy={busy_errors}"
        )
        if busy_errors == expected_busy and other_errors == 0:
            print("OK: concurrency limiter enforced as expected (extra requests refused).")
    print(f"Total elapsed: {elapsed:.4f}s")
    if results:
        total_audio = sum(r.get("audio_s", 0.0) for r in results)
        print(f"Total audio synthesized: {total_audio:.2f}s")
        print(f"Overall throughput: {total_audio/elapsed:.2f} min/min")


if __name__ == "__main__":
    main()
