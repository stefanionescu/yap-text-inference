import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioSettings:
    """SNAC/audio decode related configuration and Orpheus audio code layout."""

    # SNAC / Audio
    snac_device: str | None = None  # resolved at runtime (cuda/cpu)
    snac_max_batch: int = int(os.getenv("SNAC_MAX_BATCH", "64"))
    snac_batch_timeout_ms: int = int(os.getenv("SNAC_BATCH_TIMEOUT_MS", "2"))
    snac_sr: int = int(os.getenv("SNAC_SR", "24000"))
    tts_decode_window: int = max(int(os.getenv("TTS_DECODE_WINDOW", "28")), 28)
    tts_max_sec: float = float(os.getenv("TTS_MAX_SEC", "0"))
    snac_torch_compile: bool = bool(int(os.getenv("SNAC_TORCH_COMPILE", "0")))

    # Orpheus audio code layout
    code_offset: int = 128266
    code_size: int = 4096
    frame_substreams: int = 7
    min_window_frames: int = 4
    snac_groups: tuple[tuple[int, ...], ...] = ((0,), (1, 4), (2, 3, 5, 6))

    # PCM scaling and clipping
    pcm_clip_min: float = -1.0
    pcm_clip_max: float = 1.0
    pcm_scale: float = 32767.0

    # Decoder crop window within SNAC output (model-specific)
    snac_decode_crop_start: int = 2048
    snac_decode_crop_end: int = 4096
