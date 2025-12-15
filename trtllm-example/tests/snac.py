#!/usr/bin/env python3
"""
Minimal WebSocket client that requests SNAC tokens and prints them.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import websockets

_THIS_DIR = Path(__file__).resolve().parent
_ROOT_DIR = _THIS_DIR.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

from server.config import settings  # noqa: E402
from tests.config.audio import DEFAULT_SAMPLE_RATE  # noqa: E402
from tests.config.env import ORPHEUS_API_KEY_ENV, TTS_VOICE_ENV  # noqa: E402
from tests.config.server import DEFAULT_SERVER, SERVER_HELP  # noqa: E402
from tests.config.snac import (  # noqa: E402
    DEFAULT_FRAME_HOP_MS,
    DEFAULT_PREPAD_SILENCE_MS,
    LEADING_SILENCE_SUSTAIN_MS,
    LEADING_SILENCE_WINDOW_SEC,
    MIN_RMS_SAMPLES_FOR_PERCENTILE,
    NOISE_THRESHOLD_MULTIPLIER,
    SNAC_RESULTS_DIR,
)
from tests.config.voice import DEFAULT_VOICE, VOICE_ALIASES, VOICE_HELP  # noqa: E402
from tests.utils.audio import write_wav  # noqa: E402
from tests.utils.common import (  # noqa: E402
    DEFAULT_TEXT,
    END_SENTINEL,
    build_meta,
    websocket_connect_kwargs,
    ws_tts_url,
)
from tests.utils.paths import AUDIO_DIR  # noqa: E402

FRAME_SUBSTREAMS = settings.frame_substreams or 1
_VALID_VOICES = {alias.lower() for alias in VOICE_ALIASES}


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="SNAC token tap over WebSocket")
    ap.add_argument("--server", default=DEFAULT_SERVER, help=SERVER_HELP)
    ap.add_argument("--voice", default=os.environ.get(TTS_VOICE_ENV, DEFAULT_VOICE), help=VOICE_HELP)
    ap.add_argument("--text", default=DEFAULT_TEXT, help="Text to synthesize (token tap only)")
    ap.add_argument("--api-key", default=os.environ.get(ORPHEUS_API_KEY_ENV), help="API key (required)")
    ap.add_argument(
        "--save-audio",
        action="store_true",
        help="If set, write received PCM audio to --outfile (or a timestamped file under tests/audio)",
    )
    ap.add_argument(
        "--outfile",
        default=None,
        help="Output WAV filename when --save-audio is provided (default: tests/audio/snac_stream_<timestamp>.wav)",
    )
    ap.add_argument(
        "--print-silence",
        action="store_true",
        help="If set, print a separate object listing tokens inside the detected pre-speech window",
    )
    ap.add_argument(
        "--prepad-silence-ms",
        type=float,
        default=DEFAULT_PREPAD_SILENCE_MS,
        help="Override the prespeech pad used to classify silence tokens (default: server setting)",
    )
    ap.add_argument(
        "--save-json",
        action="store_true",
        help="If set, write SNAC token summaries to JSON under tests/snac/",
    )
    return ap.parse_args()


def _split_sentences(text: str) -> list[str]:
    return [line.strip() for line in str(text).split("\n") if line.strip()]


def _validate_voice(raw_voice: str | None) -> str:
    voice = (raw_voice or "").strip()
    if voice.lower() not in _VALID_VOICES:
        raise SystemExit("--voice must be provided as 'female' or 'male'")
    return voice


def _build_meta_payload(voice: str) -> dict:
    meta_payload = build_meta(
        voice=voice,
        trim_silence=False,
        temperature=None,
        top_p=None,
        repetition_penalty=None,
        prespeech_pad_ms=None,
    )
    meta_payload["emit_snac_tokens"] = True
    return meta_payload


async def _send_meta(ws, voice: str) -> None:
    await ws.send(json.dumps(_build_meta_payload(voice)))


async def _consume_stream(
    ws,
    *,
    sentences: list[str],
    voice: str,
) -> tuple[bytearray, list[list[dict]]]:
    pcm_buffer = bytearray()
    token_batches: list[list[dict]] = []

    async def reader():
        async for raw in ws:
            if isinstance(raw, bytes):
                pcm_buffer.extend(raw)
                continue
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("type") == "snac_tokens":
                tokens = message.get("tokens") or []
                token_batches.append([dict(token) for token in tokens])

    reader_task = asyncio.create_task(reader())
    for sentence in sentences:
        text_payload = {"text": sentence, "voice": voice, "emit_snac_tokens": True}
        await ws.send(json.dumps(text_payload))

    await ws.send(END_SENTINEL)
    await reader_task
    return pcm_buffer, token_batches


def _max_frame_index(token_batches: list[list[dict]]) -> int:
    max_frame = -1
    for batch in token_batches:
        for token in batch:
            try:
                frame_idx = int(token.get("frame_index", 0))
            except Exception:
                frame_idx = 0
            max_frame = max(max_frame, frame_idx)
    return max_frame


def _frame_hop_ms(pcm_buffer: bytearray, token_batches: list[list[dict]]) -> float:
    max_frame_index = _max_frame_index(token_batches)
    total_frames = max_frame_index + 1 if max_frame_index >= 0 else 0
    total_samples = len(pcm_buffer) // 2
    total_ms = (total_samples / DEFAULT_SAMPLE_RATE) * 1000.0 if total_samples else 0.0
    if total_frames > 0 and total_ms > 0.0:
        return total_ms / total_frames
    return DEFAULT_FRAME_HOP_MS


def _annotate_and_print_batches(token_batches: list[list[dict]], frame_hop_ms: float) -> list[dict]:
    annotated_all: list[dict] = []
    for batch_idx, batch in enumerate(token_batches):
        annotated: list[dict] = []
        for token in batch:
            frame_idx = float(token.get("frame_index", 0))
            frame_offset = float(token.get("frame_offset", 0))
            offset_ratio = (frame_offset / FRAME_SUBSTREAMS) if FRAME_SUBSTREAMS else 0.0
            timestamp_ms = (frame_idx + offset_ratio) * frame_hop_ms
            token_with_ts = dict(token)
            token_with_ts["timestamp_ms"] = round(timestamp_ms, 3)
            annotated.append(token_with_ts)
            annotated_all.append(token_with_ts)
        if annotated:
            print(f"[SNAC][batch={batch_idx}] {json.dumps(annotated)}")
    return annotated_all


def _print_silence_report(
    annotated_tokens: list[dict],
    pcm_buffer: bytearray,
    *,
    prepad_silence_ms: float,
) -> dict:
    silence_ms = compute_leading_silence_ms(bytes(pcm_buffer), prepad_silence_ms)
    silence_tokens = [tok for tok in annotated_tokens if tok.get("timestamp_ms", 0.0) <= silence_ms]
    silence_payload = {
        "type": "snac_silence",
        "silence_ms": round(silence_ms, 3),
        "tokens": silence_tokens,
    }
    print(f"[SNAC][silence <= {round(silence_ms, 3)} ms] {json.dumps(silence_payload)}")
    return silence_payload


def _write_json_outputs(annotated_tokens: list[dict], silence_payload: dict | None) -> None:
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run_dir = SNAC_RESULTS_DIR / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    tokens_path = run_dir / "snac_tokens.json"
    tokens_payload = {
        "type": "snac_tokens",
        "tokens": annotated_tokens,
    }
    tokens_path.write_text(json.dumps(tokens_payload, indent=2), encoding="utf-8")
    print(f"[snac] Wrote token JSON to {tokens_path}")

    if silence_payload:
        silence_path = run_dir / "snac_silence.json"
        silence_path.write_text(json.dumps(silence_payload, indent=2), encoding="utf-8")
        print(f"[snac] Wrote silence JSON to {silence_path}")


def _write_audio(pcm_buffer: bytearray, outfile: str | None) -> None:
    if outfile:
        out_path = Path(outfile)
    else:
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        out_path = AUDIO_DIR / f"snac_stream_{ts}.wav"

    if pcm_buffer:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        write_wav(bytes(pcm_buffer), DEFAULT_SAMPLE_RATE, out_path)
        print(f"[snac] Wrote PCM audio to {out_path}")
    else:
        print("[snac] No PCM chunks received; skipping WAV write.")


def compute_leading_silence_ms(pcm: bytes, prepad_ms: float) -> float:
    if not pcm:
        return 0.0
    sample_rate = DEFAULT_SAMPLE_RATE
    activation_ms = settings.silence_activation_ms
    rms_threshold = settings.silence_rms_threshold
    sustain_ms = LEADING_SILENCE_SUSTAIN_MS
    prepad_ms = float(prepad_ms)

    activation_samples = max(1, int(sample_rate * (activation_ms / 1000.0)))
    sustain_samples = max(
        activation_samples,
        int(sample_rate * (sustain_ms / 1000.0)),
    )

    frame = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0
    if frame.size == 0:
        return 0.0
    sq = np.square(frame, dtype=np.float32)
    if sq.size < activation_samples:
        rms = np.sqrt(np.mean(sq, dtype=np.float32)) * np.ones_like(sq)
    else:
        kernel = np.ones(activation_samples, dtype=np.float32) / float(activation_samples)
        rms = np.sqrt(np.convolve(sq, kernel, mode="same"))

    first_seg = min(rms.size, int(LEADING_SILENCE_WINDOW_SEC * sample_rate))
    base_first = float(np.median(rms[:first_seg])) if first_seg > 0 else float(np.median(rms))
    base_p20 = float(np.percentile(rms, 20)) if rms.size >= MIN_RMS_SAMPLES_FOR_PERCENTILE else base_first
    noise_floor = min(base_first, base_p20)
    threshold = max(rms_threshold, noise_floor * NOISE_THRESHOLD_MULTIPLIER)

    above = rms >= threshold
    activation_index = None
    if np.any(above):
        mask = above.astype(np.int32)
        if mask.size >= sustain_samples:
            run = np.convolve(mask, np.ones(sustain_samples, dtype=np.int32), mode="valid")
            indices = np.where(run >= sustain_samples)[0]
            if indices.size > 0:
                activation_index = int(indices[0])
    if activation_index is None and np.any(above):
        activation_index = int(np.argmax(above))
    if activation_index is None:
        activation_index = frame.size

    prepad_samples = max(0, int(sample_rate * (prepad_ms / 1000.0)))
    leading_samples = max(0, activation_index - prepad_samples)
    return (leading_samples / DEFAULT_SAMPLE_RATE) * 1000.0


async def run_snac_tap(args: argparse.Namespace) -> None:
    url = ws_tts_url(args.server)
    ws_kwargs = websocket_connect_kwargs(args.api_key, max_size=None)
    sentences = _split_sentences(args.text)

    async with websockets.connect(url, **ws_kwargs) as ws:
        voice = _validate_voice(args.voice)
        await _send_meta(ws, voice)
        pcm_buffer, token_batches = await _consume_stream(ws, sentences=sentences, voice=voice)

    frame_hop_ms = _frame_hop_ms(pcm_buffer, token_batches)
    annotated_all = _annotate_and_print_batches(token_batches, frame_hop_ms)

    silence_payload: dict | None = None
    if args.print_silence:
        silence_payload = _print_silence_report(
            annotated_all,
            pcm_buffer,
            prepad_silence_ms=args.prepad_silence_ms,
        )

    if args.save_json:
        _write_json_outputs(annotated_all, silence_payload)

    if args.save_audio:
        _write_audio(pcm_buffer, args.outfile)


def main() -> None:
    args = parse_args()
    asyncio.run(run_snac_tap(args))


if __name__ == "__main__":
    main()
