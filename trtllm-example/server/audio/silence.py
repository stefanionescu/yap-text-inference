"""Leading silence trimming utilities for streaming audio chunks."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class SilenceTrimConfig:
    """Configuration knobs for `SilenceTrimmer`."""

    sample_rate: int
    enabled: bool
    rms_threshold: float
    activation_ms: float
    prepad_ms: float
    max_leading_sec: float
    sustain_ms: float
    noise_window_sec: float
    noise_percentile: float
    threshold_multiplier: float


class SilenceTrimmer:
    """Drops leading silence by buffering until speech activation is detected."""

    _DEFAULT_SUSTAIN_MS = 30.0  # Require speech to sustain for this many ms before unmuting
    _DEFAULT_NOISE_WINDOW_SEC = 0.4
    _DEFAULT_NOISE_PERCENTILE = 20.0
    _DEFAULT_THRESHOLD_MULTIPLIER = 4.0
    _MIN_RMS_SAMPLES = 5  # Minimum samples required for percentile calculation
    _PERCENTILE_MAX = 100.0  # Maximum valid percentile value

    def __init__(self, cfg: SilenceTrimConfig):
        self.cfg = cfg
        self._started = not cfg.enabled
        self._sample_rate = cfg.sample_rate
        self._activation_samples = max(1, int(cfg.sample_rate * (cfg.activation_ms / 1000.0)))
        sustain_ms = cfg.sustain_ms if cfg.sustain_ms > 0 else self._DEFAULT_SUSTAIN_MS
        sustain_samples = max(1, int(cfg.sample_rate * (sustain_ms / 1000.0)))
        self._sustain_samples = max(self._activation_samples, sustain_samples)
        self._max_leading_samples = int(cfg.sample_rate * cfg.max_leading_sec) if cfg.max_leading_sec > 0 else None
        self._prepad_samples = max(0, int(cfg.sample_rate * (cfg.prepad_ms / 1000.0)))
        noise_window = cfg.noise_window_sec if cfg.noise_window_sec > 0 else self._DEFAULT_NOISE_WINDOW_SEC
        self._noise_window_samples = max(1, int(cfg.sample_rate * noise_window))
        percentile = cfg.noise_percentile if cfg.noise_percentile >= 0 else self._DEFAULT_NOISE_PERCENTILE
        self._noise_percentile = max(0.0, min(100.0, float(percentile)))
        multiplier = cfg.threshold_multiplier if cfg.threshold_multiplier > 0 else self._DEFAULT_THRESHOLD_MULTIPLIER
        self._threshold_multiplier = float(multiplier)
        self._pending = bytearray()

    def push(self, audio_bytes: bytes) -> bytes:
        """Process a PCM chunk and return trimmed bytes if leading silence remains."""
        if not audio_bytes:
            return b""
        if self._started:
            return audio_bytes

        self._pending.extend(audio_bytes)
        pending_frame = np.frombuffer(self._pending, dtype=np.int16).copy()
        if pending_frame.size == 0:
            return b""

        activation_index = self._detect_activation(pending_frame)
        if activation_index is None:
            if self._max_leading_samples is not None and pending_frame.size >= self._max_leading_samples:
                activation_index = pending_frame.size
            else:
                return b""

        return self._emit_from_activation(pending_frame, activation_index)

    def flush(self) -> bytes:
        """Ensure downstream consumers know we won't emit more audio."""
        if not self._started and self._pending:
            pending_frame = np.frombuffer(self._pending, dtype=np.int16).copy()
            activation_index = self._detect_activation(pending_frame)
            if activation_index is None:
                activation_index = pending_frame.size
            return self._emit_from_activation(pending_frame, activation_index)
        self._started = True
        return b""

    def _emit_from_activation(self, frame: np.ndarray, activation_index: int) -> bytes:
        if activation_index is None:
            return b""
        activation_index = max(0, min(int(activation_index), frame.size))
        start_idx = max(0, activation_index - self._prepad_samples)
        emit = frame[start_idx:].tobytes()
        self._pending = bytearray()
        self._started = True
        return emit

    def _detect_activation(self, frame: np.ndarray) -> int | None:
        """Detect first activation index using short-time RMS with sustain + dynamic threshold."""
        if frame.size == 0:
            return None

        float_frame = frame.astype(np.float32) / 32768.0
        sq = np.square(float_frame, dtype=np.float32)

        win = self._activation_samples
        if sq.size < win:
            rms = np.sqrt(np.mean(sq, dtype=np.float32)) * np.ones_like(sq)
        else:
            kernel = np.ones(win, dtype=np.float32) / float(win)
            rms = np.sqrt(np.convolve(sq, kernel, mode="same"))

        threshold = self._dynamic_threshold(rms)
        above = rms >= threshold
        if not np.any(above):
            return None

        mask = above.astype(np.int32)
        sustain = self._sustain_samples
        if mask.size >= sustain:
            run = np.convolve(mask, np.ones(sustain, dtype=np.int32), mode="valid")
            indices = np.where(run >= sustain)[0]
            if indices.size > 0:
                return int(indices[0])

        return int(np.argmax(above))

    def _dynamic_threshold(self, rms: np.ndarray) -> float:
        if rms.size == 0:
            return self.cfg.rms_threshold

        first_seg = min(rms.size, self._noise_window_samples)
        base_first = float(np.median(rms[:first_seg])) if first_seg > 0 else float(np.median(rms))
        if rms.size >= self._MIN_RMS_SAMPLES and 0.0 <= self._noise_percentile <= self._PERCENTILE_MAX:
            base_percentile = float(np.percentile(rms, self._noise_percentile))
        else:
            base_percentile = base_first
        noise_floor = min(base_first, base_percentile)
        return max(self.cfg.rms_threshold, noise_floor * self._threshold_multiplier)
