import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SilenceSettings:
    """Audio post-processing: leading silence trimming configuration."""

    trim_leading_silence: bool = os.getenv("TRIM_LEADING_SILENCE", "1") == "1"
    # Slightly relax trimming (a bit more leading silence by default)
    silence_rms_threshold: float = float(os.getenv("SILENCE_RMS_THRESHOLD", "0.0030"))
    silence_activation_ms: float = float(os.getenv("SILENCE_ACTIVATION_MS", "10"))
    silence_prespeech_pad_ms: float = float(os.getenv("SILENCE_PRESPEECH_PAD_MS", "160"))
    silence_max_leading_sec: float = float(os.getenv("SILENCE_MAX_LEADING_SEC", "1.0"))
    # API validation bounds for per-request override (read env, then clamp to 50–700)
    _prespeech_min_env = float(os.getenv("SILENCE_PRESPEECH_MIN_MS", "50"))
    _prespeech_max_env = float(os.getenv("SILENCE_PRESPEECH_MAX_MS", "700"))

    _prespeech_min = max(50.0, min(700.0, _prespeech_min_env))
    _prespeech_max = max(50.0, min(700.0, _prespeech_max_env))
    _prespeech_max = max(_prespeech_max, _prespeech_min)
    silence_prespeech_min_ms: float = _prespeech_min
    silence_prespeech_max_ms: float = _prespeech_max
