from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from tests.config.audio import (  # noqa: E402
    DEFAULT_SAMPLE_RATE,
    LEADING_SILENCE_NOISE_PERCENTILE,
    LEADING_SILENCE_NOISE_WINDOW_SEC,
    LEADING_SILENCE_RMS_WINDOW_MS,
    LEADING_SILENCE_SUSTAIN_MS,
    LEADING_SILENCE_THRESHOLD_DBFS,
    LEADING_SILENCE_THRESHOLD_MULTIPLIER,
    PCM_CHANNELS,
    PCM_SAMPLE_WIDTH_BYTES,
)


def write_wav(pcm_data: bytes, sample_rate: int, out_path: Path) -> float:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(PCM_CHANNELS)
        wf.setsampwidth(PCM_SAMPLE_WIDTH_BYTES)  # 16-bit PCM
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    # PCM16 sample width is 2 bytes
    return (len(pcm_data) / PCM_SAMPLE_WIDTH_BYTES) / float(sample_rate) if pcm_data else 0.0


def _dbfs_to_linear(db: float) -> float:
    """Convert dBFS to linear amplitude in range [0,1]."""
    return float(10.0 ** (db / 20.0))


def leading_silence_ms(
    pcm_data: bytes,
    sample_rate: int = DEFAULT_SAMPLE_RATE,
    threshold_dbfs: float = LEADING_SILENCE_THRESHOLD_DBFS,
    rms_window_ms: float = LEADING_SILENCE_RMS_WINDOW_MS,
    min_sustain_ms: float = LEADING_SILENCE_SUSTAIN_MS,
) -> float:
    """
    Estimate leading silence duration by analyzing PCM16 mono audio.

    Method:
    1) Short-time RMS with a robust dynamic threshold:
       threshold = max(fixed dBFS, 4x noise_floor), where noise_floor is the
       minimum of (median RMS over first 0.4s, 20th percentile RMS over full clip).
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

    # Robust noise floor:
    # - Median of the first 0.4s (captures trimmed or untrimmed prespeech)
    # - 20th percentile of the whole clip (resists occasional early bursts)
    first_seg_len = min(rms.size, int(LEADING_SILENCE_NOISE_WINDOW_SEC * sample_rate))
    base_first = float(np.median(rms[:first_seg_len])) if first_seg_len > 0 else float(np.median(rms))
    base_p20 = float(np.percentile(rms, LEADING_SILENCE_NOISE_PERCENTILE)) if rms.size > 0 else base_first
    noise_floor = min(base_first, base_p20)

    # Dynamic threshold: relative to noise floor with an absolute floor (in dBFS)
    thr_dynamic = max(thr_fixed, noise_floor * LEADING_SILENCE_THRESHOLD_MULTIPLIER)

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
            # 'valid' convolution yields indices aligned to the original signal start
            start_idx = idx_rel
        else:
            # Fallback: first above-threshold sample
            start_idx = int(np.argmax(above))
    else:
        start_idx = int(np.argmax(above))

    # Clamp and compute ms
    start_idx = max(0, min(start_idx, samples.size))
    return (float(start_idx) * 1000.0) / float(sample_rate)
