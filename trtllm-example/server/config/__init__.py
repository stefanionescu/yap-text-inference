"""Unified configuration access with both namespaced and flat lookups."""

from dataclasses import dataclass
from typing import Any

from .audio import AudioSettings
from .engine import EngineSettings
from .model import ModelSettings
from .runtime import RuntimeSettings
from .server import ServerSettings
from .silence import SilenceSettings
from .streaming import StreamingSettings
from .voices import VoiceSettings
from .websocket import WebSocketSettings


@dataclass(frozen=True)
class Settings:
    """
    Aggregate configuration sections under a single object.

    Access patterns:
        settings.streaming.default_temperature  # preferred, explicit section
        settings.default_temperature            # legacy flat access (via __getattr__)
    """

    server: ServerSettings = ServerSettings()
    model: ModelSettings = ModelSettings()
    engine: EngineSettings = EngineSettings()
    streaming: StreamingSettings = StreamingSettings()
    audio: AudioSettings = AudioSettings()
    websocket: WebSocketSettings = WebSocketSettings()
    runtime: RuntimeSettings = RuntimeSettings()
    silence: SilenceSettings = SilenceSettings()
    voices: VoiceSettings = VoiceSettings()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_sections",
            (
                self.server,
                self.model,
                self.engine,
                self.streaming,
                self.audio,
                self.websocket,
                self.runtime,
                self.silence,
                self.voices,
            ),
        )

    def __getattr__(self, name: str) -> Any:
        for section in getattr(self, "_sections", ()):
            if hasattr(section, name):
                return getattr(section, name)
        raise AttributeError(name)

    def describe_sections(self) -> dict[str, str]:
        """Return a summary of section docstrings for developer onboarding."""
        return {
            "server": (ServerSettings.__doc__ or "").strip(),
            "model": (ModelSettings.__doc__ or "").strip(),
            "engine": (EngineSettings.__doc__ or "").strip(),
            "streaming": (StreamingSettings.__doc__ or "").strip(),
            "audio": (AudioSettings.__doc__ or "").strip(),
            "websocket": (WebSocketSettings.__doc__ or "").strip(),
            "runtime": (RuntimeSettings.__doc__ or "").strip(),
            "silence": (SilenceSettings.__doc__ or "").strip(),
            "voices": (VoiceSettings.__doc__ or "").strip(),
        }


settings = Settings()

__all__ = [
    "Settings",
    "settings",
    "ServerSettings",
    "ModelSettings",
    "EngineSettings",
    "StreamingSettings",
    "AudioSettings",
    "WebSocketSettings",
    "RuntimeSettings",
    "SilenceSettings",
    "VoiceSettings",
]
