import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ServerSettings:
    """Core server configuration."""

    # Server
    host: str = os.getenv("HOST", "0.0.0.0")  # noqa: S104 (needed for container networking)
    port: int = int(os.getenv("PORT", "8000"))
    api_title: str = os.getenv("API_TITLE", "Orpheus 3B TTS API for Yap")
    http_health_path: str = os.getenv("HTTP_HEALTH_PATH", "/healthz")
