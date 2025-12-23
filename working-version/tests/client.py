#!/usr/bin/env python3
"""
Orpheus TTS WebSocket client.

- Connects to a remote Orpheus TTS server (cloud or local)
- Sends a single JSON payload with full text and receives streaming PCM chunks
- Aggregates all audio and saves a WAV file under ROOT/audio/
- Tracks metrics similar to other test files (TTFB, connect, handshake)
- Supports env vars: CLOUD_TCP_HOST, CLOUD_TCP_PORT
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
from dotenv import load_dotenv

# Ensure repository root is on sys.path so `server` package is importable
_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

# Load .env from repository root so env defaults are available (CLI overrides)
load_dotenv(_ROOT_DIR / ".env")

from server.text.prompts import chunk_by_sentences  # noqa: E402
from tests.config.audio import DEFAULT_SAMPLE_RATE  # noqa: E402
from tests.config.env import (  # noqa: E402
    CLOUD_TCP_HOST_ENV,
    CLOUD_TCP_PORT_ENV,
    ORPHEUS_API_KEY_ENV,
    SERVER_URL_ENV,
    TTS_VOICE_ENV,
)
from tests.config.generation import (  # noqa: E402
    DEFAULT_TRIM_SILENCE,
    PRESPEECH_PAD_MS_HELP,
    REPETITION_PENALTY_HELP,
    TEMPERATURE_HELP,
    TOP_P_HELP,
)
from tests.config.server import DEFAULT_HOST, DEFAULT_PORT  # noqa: E402
from tests.config.voice import DEFAULT_VOICE, VOICE_HELP  # noqa: E402
from tests.utils.audio import (  # noqa: E402
    leading_silence_ms,  # noqa: E402
    write_wav,  # noqa: E402
)
from tests.utils.common import (  # noqa: E402
    DEFAULT_TEXT,
    END_SENTINEL,
    build_meta,
    build_server_base,
    parse_bool,
    websocket_connect_kwargs,
    ws_tts_url,
)
from tests.utils.paths import AUDIO_DIR  # noqa: E402
from tests.utils.report import print_client_result, report_sentence_mismatch  # noqa: E402
from tests.utils.stream import recv_pcm_and_sentences  # noqa: E402


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Orpheus TTS WebSocket Client")
    ap.add_argument(
        "--server",
        default=os.getenv(SERVER_URL_ENV, ""),
        help="Full server URL or host:port (overrides --host/--port)",
    )
    ap.add_argument(
        "--host",
        default=(os.getenv(CLOUD_TCP_HOST_ENV) or DEFAULT_HOST),
        help="Cloud public host (defaults to CLOUD_TCP_HOST or 127.0.0.1)",
    )
    ap.add_argument(
        "--port",
        type=int,
        default=(int(os.getenv(CLOUD_TCP_PORT_ENV) or DEFAULT_PORT)),
        help="Cloud public port (defaults to CLOUD_TCP_PORT or 8000)",
    )
    ap.add_argument(
        "--secure",
        action="store_true",
        help="Use wss:// (TLS); auto-enabled for cloud proxy hosts",
    )
    ap.add_argument(
        "--voice",
        default=os.getenv(TTS_VOICE_ENV, DEFAULT_VOICE),
        help=VOICE_HELP,
    )
    ap.add_argument(
        "--text",
        action="append",
        default=None,
        help="Text to synthesize (repeat flag for multiple sentences)",
    )
    ap.add_argument(
        "--api-key",
        default=os.getenv(ORPHEUS_API_KEY_ENV),
        help="API key (required)",
    )
    ap.add_argument(
        "--outfile",
        default=None,
        help="Output WAV filename (default: tts_<timestamp>.wav under ROOT/audio)",
    )
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
    return ap.parse_args()


def _compose_server_from_host_port(host: str, port: int, secure: bool) -> str:
    return build_server_base(None, host, port, secure)


async def tts_client(  # noqa: PLR0913
    server: str,
    voice: str,
    texts: list[str],
    api_key: str | None,
    out_path: Path,
    trim_silence: bool,
    temperature: float | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    prespeech_pad_ms: float | None = None,
) -> dict:
    url = ws_tts_url(server)
    ws_kwargs = websocket_connect_kwargs(api_key, max_size=None)

    t0_e2e = time.perf_counter()
    t0_server: float | None = None

    sample_rate = DEFAULT_SAMPLE_RATE
    connect_ms = 0.0

    full_text = " ".join(texts).strip()
    sentences = [s for s in chunk_by_sentences(full_text) if s and s.strip()]

    connect_start = time.perf_counter()
    async with websockets.connect(url, **ws_kwargs) as ws:
        connect_ms += (time.perf_counter() - connect_start) * 1000.0

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

    if recv_sentences != sentences:
        report_sentence_mismatch("CLIENT", sentences, recv_sentences)

    wall_s = time.perf_counter() - t0_e2e

    if not pcm_data:
        raise RuntimeError("No audio data received from server")

    audio_s = write_wav(pcm_data, sample_rate, out_path)
    lead_ms = float(leading_silence_ms(pcm_data, sample_rate)) if pcm_data else 0.0

    metrics = {
        "server": server,
        "trim_silence": bool(trim_silence),
        "prespeech_pad_ms": (float(prespeech_pad_ms) if prespeech_pad_ms is not None else None),
        "voice": voice,
        "outfile": str(out_path),
        "wall_s": float(wall_s),
        "audio_s": float(audio_s),
        "ttfb_e2e_s": float((first_chunk_at - t0_e2e) if first_chunk_at else 0.0),
        "ttfb_server_s": float((first_chunk_at - t0_server) if (first_chunk_at and t0_server) else 0.0),
        "connect_ms": float(connect_ms),
        "rtf": float(wall_s / audio_s) if audio_s > 0 else float("inf"),
        "xrt": float(audio_s / wall_s) if wall_s > 0 else 0.0,
        "leading_silence_ms": lead_ms,
    }

    return metrics


def main() -> None:
    args = parse_args()
    texts = [t for t in (args.text or [DEFAULT_TEXT]) if t and t.strip()]

    if not args.api_key:
        raise SystemExit("Missing API key. Set ORPHEUS_API_KEY in .env or pass --api-key.")

    # Build server string from args/env
    server_str = (args.server or "").strip()
    if not server_str:
        host = args.host
        port = args.port
        server_str = _compose_server_from_host_port(host, port, args.secure)

    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    out = Path(args.outfile) if args.outfile else (AUDIO_DIR / f"tts_{ts}.wav")

    print(f"Server: {server_str}")
    print(f"Voice:  {args.voice}")
    print(f"Out:    {out}")
    print(f"Text(s): {len(texts)}")

    trim_flag = parse_bool(args.trim_silence)
    res = asyncio.run(
        tts_client(
            server_str,
            args.voice,
            texts,
            args.api_key,
            out,
            trim_flag,
            args.temperature,
            getattr(args, "top_p", None),
            getattr(args, "repetition_penalty", None),
            getattr(args, "prespeech_pad_ms", None),
        )
    )

    print_client_result(res)


if __name__ == "__main__":
    main()
