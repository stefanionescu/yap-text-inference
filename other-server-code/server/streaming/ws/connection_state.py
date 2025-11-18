"""Per-connection synthesis state management.

Each class in this package is defined in its own module for modularity.
"""

from server.config import settings
from server.voices import get_voice_defaults, resolve_voice

__all__ = ["ConnectionState", "InvalidMetaError"]


class InvalidMetaError(ValueError):
    """Raised when websocket metadata payloads fail validation."""


class ConnectionState:
    """Manages per-connection synthesis parameters."""

    def __init__(self):
        # Voice must be explicitly provided by the client via meta or per-message override
        self.voice = None
        self.temperature: float | None = None
        self.top_p: float | None = None
        self.repetition_penalty: float | None = None
        # Default to global setting; clients can override per-connection or per-text
        self.trim_silence: bool = bool(settings.trim_leading_silence)
        # Optional per-connection override for pre-speech pad (ms)
        self.prespeech_pad_ms: float | None = None

    def update_from_meta(self, meta: dict) -> None:
        """Update connection state from metadata message."""
        self._update_voice_from_meta(meta)
        self._update_temperature_from_meta(meta)
        self._update_top_p_from_meta(meta)
        self._update_repetition_penalty_from_meta(meta)
        self._update_trim_silence_from_meta(meta)
        self._update_prespeech_from_meta(meta)

    def get_sampling_kwargs(self) -> dict:
        """Build sampling parameters dict with voice-specific fallback defaults."""
        # Voice must have been set by now via meta or message override
        if not self.voice:
            raise InvalidMetaError("Voice not set; client must provide 'voice' in metadata or per message.")
        voice_defaults = get_voice_defaults(self.voice)

        return {
            "temperature": float(self.temperature if self.temperature is not None else voice_defaults["temperature"]),
            "top_p": float(self.top_p if self.top_p is not None else voice_defaults["top_p"]),
            "repetition_penalty": float(
                self.repetition_penalty if self.repetition_penalty is not None else voice_defaults["repetition_penalty"]
            ),
            # Server-enforced output length; not client-overridable
            "max_tokens": int(settings.orpheus_max_tokens),
            "stop_token_ids": list(settings.server_stop_token_ids),
        }

    # --- Internal helpers ---

    def _update_voice_from_meta(self, meta: dict) -> None:
        if "voice" in meta and meta["voice"]:
            try:
                voice_str = str(meta["voice"])
                resolve_voice(voice_str)
                self.voice = voice_str
            except ValueError as e:
                raise InvalidMetaError(f"Voice validation failed: {e}") from e

    def _update_temperature_from_meta(self, meta: dict) -> None:
        if settings.ws_key_temperature in meta:
            try:
                value = float(meta[settings.ws_key_temperature])
            except (ValueError, TypeError) as exc:
                raise InvalidMetaError(f"Invalid temperature parameter: {exc}") from exc
            if settings.temperature_min <= value <= settings.temperature_max:
                self.temperature = value
            else:
                raise InvalidMetaError(
                    "Temperature must be between "
                    f"{settings.temperature_min} and {settings.temperature_max}, got {value}"
                )

    def _update_top_p_from_meta(self, meta: dict) -> None:
        if settings.ws_key_top_p in meta:
            try:
                value = float(meta[settings.ws_key_top_p])
            except (ValueError, TypeError) as exc:
                raise InvalidMetaError(f"Invalid top_p parameter: {exc}") from exc
            if settings.top_p_min <= value <= settings.top_p_max:
                self.top_p = value
            else:
                raise InvalidMetaError(
                    "top_p must be between " f"{settings.top_p_min} and {settings.top_p_max}, got {value}"
                )

    def _update_repetition_penalty_from_meta(self, meta: dict) -> None:
        if settings.ws_key_repetition_penalty in meta:
            try:
                value = float(meta[settings.ws_key_repetition_penalty])
            except (ValueError, TypeError) as exc:
                raise InvalidMetaError(f"Invalid repetition_penalty parameter: {exc}") from exc
            if settings.repetition_penalty_min <= value <= settings.repetition_penalty_max:
                self.repetition_penalty = value
            else:
                raise InvalidMetaError(
                    "repetition_penalty must be between "
                    f"{settings.repetition_penalty_min} and {settings.repetition_penalty_max}, got {value}"
                )

    def _update_trim_silence_from_meta(self, meta: dict) -> None:
        if settings.ws_key_trim_silence in meta:
            val = meta[settings.ws_key_trim_silence]
            import contextlib

            with contextlib.suppress(Exception):
                if isinstance(val, bool):
                    self.trim_silence = val
                elif isinstance(val, str):
                    self.trim_silence = val.strip().lower() in set(settings.ws_truthy_values)
                else:
                    self.trim_silence = bool(int(val))

    def _update_prespeech_from_meta(self, meta: dict) -> None:
        if settings.ws_key_prespeech_pad_ms in meta:
            try:
                value = float(meta[settings.ws_key_prespeech_pad_ms])
            except (ValueError, TypeError) as exc:
                raise InvalidMetaError(f"Invalid prespeech_pad_ms parameter: {exc}") from exc
            if settings.silence_prespeech_min_ms <= value <= settings.silence_prespeech_max_ms:
                self.prespeech_pad_ms = value
            else:
                raise InvalidMetaError(
                    "prespeech_pad_ms must be between "
                    f"{settings.silence_prespeech_min_ms} and {settings.silence_prespeech_max_ms}, got {value}"
                )
