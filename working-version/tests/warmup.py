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
from tests.config.audio import DEFAULT_SAMPLE_RATE  # noqa: E402
from tests.config.env import ORPHEUS_API_KEY_ENV, TTS_VOICE_ENV  # noqa: E402
from tests.config.generation import (  # noqa: E402
    DEFAULT_TRIM_SILENCE,
    PRESPEECH_PAD_MS_HELP,
    REPETITION_PENALTY_HELP,
    TEMPERATURE_HELP,
    TOP_P_HELP,
)
from tests.config.server import DEFAULT_SERVER, SERVER_HELP  # noqa: E402
from tests.config.voice import DEFAULT_VOICE, VOICE_ALIASES, VOICE_HELP  # noqa: E402
from tests.utils.audio import leading_silence_ms  # noqa: E402
from tests.utils.common import (  # noqa: E402
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
    ap.add_argument("--server", default=DEFAULT_SERVER, help=SERVER_HELP)
    ap.add_argument(
        "--voice",
        default=os.environ.get(TTS_VOICE_ENV, DEFAULT_VOICE),
        help=f"{VOICE_HELP} (required)",
    )
    ap.add_argument("--text", default=DEFAULT_TEXT, help="Text to synthesize")
    ap.add_argument("--api-key", default=os.environ.get(ORPHEUS_API_KEY_ENV), help="API key (required)")
    ap.add_argument(
        "--trim-silence",
        default=DEFAULT_TRIM_SILENCE,
        help="Trim leading silence on server (true|false)",
    )
    ap.add_argument(
        "--temperature",
        type=float,
        default=None,
        help=TEMPERATURE_HELP,
    )
    ap.add_argument(
        "--top-p",
        type=float,
        default=None,
        help=TOP_P_HELP,
    )
    ap.add_argument(
        "--repetition-penalty",
        type=float,
        default=None,
        help=REPETITION_PENALTY_HELP,
    )
    ap.add_argument(
        "--prespeech-pad-ms",
        type=float,
        default=None,
        help=PRESPEECH_PAD_MS_HELP,
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
            if voice.lower() not in {alias.lower() for alias in VOICE_ALIASES}:
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
        "trim_silence": parse_bool(args.trim_silence),
        "prespeech_pad_ms": (float(args.prespeech_pad_ms) if args.prespeech_pad_ms is not None else None),
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
