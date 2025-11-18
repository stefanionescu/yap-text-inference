#!/usr/bin/env python3
"""
Single WebSocket streaming warmup for Orpheus TTS server.
Sends text over WS and measures bytes of streamed PCM.
"""

from __future__ import annotations

import argparse
import asyncio
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
    parse_bool,
    websocket_connect_kwargs,
    ws_tts_url,
)
from tests.utils.report import print_client_result, report_sentence_mismatch  # noqa: E402
from tests.utils.stream import recv_pcm_and_sentences  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="WebSocket streaming warmup (Orpheus TTS)")
    ap.add_argument("--server", default="127.0.0.1:8000", help="host:port or http[s]://host:port")
    ap.add_argument(
        "--voice", default=os.environ.get("TTS_VOICE", "female"), help="Voice alias: female|male (required)"
    )
    ap.add_argument("--text", default=DEFAULT_TEXT, help="Text to synthesize")
    ap.add_argument("--api-key", default=os.environ.get("ORPHEUS_API_KEY"), help="API key (required)")
    ap.add_argument("--trim-silence", default="true", help="Trim leading silence on server (true|false)")
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
    ap.add_argument(
        "--prespeech-pad-ms",
        type=float,
        default=None,
        help="Pre-speech pad in ms when trimming (50-700). Omit to use server default",
    )
    args = ap.parse_args()

    url = ws_tts_url(args.server)
    t0_e2e = time.perf_counter()
    sr = DEFAULT_SAMPLE_RATE
    t0_server: float | None = None

    async def run():
        nonlocal t0_server
        sentences = [s for s in chunk_by_sentences(str(args.text)) if s and s.strip()]
        ws_kwargs = websocket_connect_kwargs(args.api_key, max_size=None)
        async with websockets.connect(url, **ws_kwargs) as ws:
            # Send metadata first
            trim_flag = parse_bool(args.trim_silence)
            voice = (args.voice or "").strip()
            if voice.lower() not in {"female", "male"}:
                raise SystemExit("--voice must be provided as 'female' or 'male'")
            await ws.send(
                json.dumps(
                    build_meta(
                        voice,
                        trim_flag,
                        args.temperature,
                        getattr(args, "top_p", None),
                        getattr(args, "repetition_penalty", None),
                        getattr(args, "prespeech_pad_ms", None),
                    )
                )
            )

            recv_task = asyncio.create_task(recv_pcm_and_sentences(ws))

            for _idx, sentence in enumerate(sentences):
                await ws.send(json.dumps({"text": sentence.strip(), "voice": voice}))
                if t0_server is None:
                    t0_server = time.perf_counter()

            await ws.send(END_SENTINEL)
            pcm_data, recv_sentences, first_chunk_at = await recv_task

            if recv_sentences != sentences:
                report_sentence_mismatch("WARMUP", sentences, recv_sentences)
            return pcm_data, first_chunk_at, t0_server

    pcm_data, first_chunk_at, t0_server = asyncio.run(run())

    wall_s = time.perf_counter() - t0_e2e
    ttfb_e2e_s = (first_chunk_at - t0_e2e) if first_chunk_at else 0.0
    ttfb_server_s = (first_chunk_at - t0_server) if (first_chunk_at and t0_server) else 0.0
    audio_s = (len(pcm_data) / 2.0) / float(sr) if pcm_data else 0.0
    rtf = (wall_s / audio_s) if audio_s > 0 else float("inf")
    xrt = (audio_s / wall_s) if wall_s > 0 else 0.0
    lead_ms = float(leading_silence_ms(pcm_data, sr)) if pcm_data else 0.0

    metrics = {
        "server": args.server,
        "voice": args.voice,
        "text": str(args.text),
        "wall_s": float(wall_s),
        "audio_s": float(audio_s),
        "ttfb_e2e_s": float(ttfb_e2e_s),
        "ttfb_server_s": float(ttfb_server_s),
        "rtf": float(rtf),
        "xrt": float(xrt),
        "leading_silence_ms": lead_ms,
    }
    print_client_result(metrics, header="Warmup TTS request")


if __name__ == "__main__":
    main()
