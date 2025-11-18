from __future__ import annotations

import wave
from pathlib import Path

import numpy as np


def write_wav(pcm_data: bytes, sample_rate: int, out_path: Path) -> float:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    # 16-bit PCM = 2 bytes/sample
    return (len(pcm_data) / 2.0) / float(sample_rate) if pcm_data else 0.0


def _dbfs_to_linear(db: float) -> float:
    """Convert dBFS to linear amplitude in range [0,1]."""
    return float(10.0 ** (db / 20.0))


def leading_silence_ms(
    pcm_data: bytes,
    sample_rate: int,
    threshold_dbfs: float = -30.0,
    rms_window_ms: float = 10.0,
    min_sustain_ms: float = 30.0,
) -> float:
    """
    Estimate leading silence duration by analyzing PCM16 mono audio.

    Method:
    1) Short-time RMS with dynamic threshold: threshold is max(fixed dBFS, 4x baseline RMS from first 0.5s).
    2) Require sustain above threshold for a short duration to avoid transient spikes.

    Returns milliseconds of silence before first audible content. If no audible
    content found above threshold, returns total audio duration in ms.
    """
    if not pcm_data:
        return 0.0

    # Interpret little-endian PCM16 mono
    samples = np.frombuffer(pcm_data, dtype=np.int16)
    if samples.size == 0:
        return 0.0

    # Normalize to [-1, 1] float for stable RMS math
    x = samples.astype(np.float32) / 32768.0

    # Parameters → samples
    win = max(1, int(round((rms_window_ms / 1000.0) * sample_rate)))
    sustain = max(1, int(round((min_sustain_ms / 1000.0) * sample_rate)))
    thr_fixed = _dbfs_to_linear(threshold_dbfs)

    # Short-time RMS using moving average on squared signal
    # Use 'same' to keep alignment with original indices.
    sq = np.square(x, dtype=np.float32)
    kernel = np.ones(win, dtype=np.float32) / float(win)
    # Handle extremely short clips gracefully (len < win)
    if sq.size < win:
        rms = np.sqrt(np.mean(sq, dtype=np.float32)) * np.ones_like(sq)
    else:
        rms = np.sqrt(np.convolve(sq, kernel, mode="same"))

    # Dynamic threshold: estimate baseline from first 0.5s (or full clip if shorter)
    first_half_s = min(samples.size, int(0.5 * sample_rate))
    base_rms = float(np.median(rms[:first_half_s])) if first_half_s > 0 else float(np.median(rms))
    thr_dynamic = max(thr_fixed, base_rms * 4.0)

    # Detection with sustain to avoid single-sample spikes
    above = rms >= thr_dynamic
    if not np.any(above):
        # Entire clip under threshold → treat as all silence
        return float(samples.size) * 1000.0 / float(sample_rate)

    # Running sum over boolean mask to find first sustained region
    mask = above.astype(np.int32)
    if mask.size >= sustain:
        run = np.convolve(mask, np.ones(sustain, dtype=np.int32), mode="valid")
        if np.any(run >= sustain):
            idx_rel = int(np.argmax(run >= sustain))
            start_idx = idx_rel  # already aligned to original indices due to 'valid'
        else:
            # Fallback: first above-threshold sample
            start_idx = int(np.argmax(above))
    else:
        start_idx = int(np.argmax(above))

    # Clamp and compute ms
    start_idx = max(0, min(start_idx, samples.size))
    return (float(start_idx) * 1000.0) / float(sample_rate)
