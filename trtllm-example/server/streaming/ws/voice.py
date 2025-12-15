"""Voice validation helpers for WebSocket synthesis."""

from __future__ import annotations

from dataclasses import dataclass

from server.config import settings
from server.streaming.ws.connection_state import ConnectionState
from server.voices import resolve_voice

__all__ = ["VoiceValidator", "VoiceValidationError"]


class VoiceValidationError(ValueError):
    """Raised when a text message lacks a valid voice selection."""


@dataclass(slots=True)
class VoiceValidator:
    """Ensure each text message uses a valid voice (meta or per-message override)."""

    def ensure_voice(self, message: dict, connection_state: ConnectionState) -> str:
        if settings.ws_key_voice in message:
            voice_override = message.get(settings.ws_key_voice)
            voice_str = str(voice_override or "").strip()
            resolve_voice(voice_str)  # validate alias → raises if invalid
            connection_state.voice = voice_str
            return voice_str

        if connection_state.voice:
            return connection_state.voice

        raise VoiceValidationError("Voice must be provided via metadata before streaming text.")
