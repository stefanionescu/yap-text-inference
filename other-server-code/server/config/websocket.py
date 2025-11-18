import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WebSocketSettings:
    """WebSocket protocol configuration and simple API auth."""

    # WebSocket protocol defaults
    ws_end_sentinel: str = os.getenv("WS_END_SENTINEL", "__END__")
    ws_cancel_sentinel: str = os.getenv("WS_CANCEL_SENTINEL", "__CANCEL__")
    ws_close_busy_code: int = int(os.getenv("WS_CLOSE_BUSY_CODE", "1013"))
    ws_close_internal_code: int = int(os.getenv("WS_CLOSE_INTERNAL_CODE", "1011"))
    ws_close_unauthorized_code: int = int(os.getenv("WS_CLOSE_UNAUTHORIZED_CODE", "1008"))
    ws_queue_maxsize: int = int(os.getenv("WS_QUEUE_MAXSIZE", "128"))
    ws_tts_path: str = os.getenv("WS_TTS_PATH", "/ws/tts")
    default_voice: str = os.getenv("DEFAULT_VOICE", "tara")
    # Max concurrent websocket connections (server-wide)
    ws_max_connections: int = int(os.getenv("WS_MAX_CONNECTIONS", "16"))
    # Session lifecycle
    ws_session_ttl_s: float = float(os.getenv("WS_SESSION_TTL_S", "5400"))  # 90 minutes
    ws_idle_timeout_s: float = float(os.getenv("WS_IDLE_TIMEOUT_S", "150"))  # 2.5 minutes
    # Watchdog and handshake tuning
    ws_watchdog_tick_s: float = float(os.getenv("WS_WATCHDOG_TICK_S", "5"))  # watchdog check interval
    ws_handshake_acquire_timeout_s: float = float(os.getenv("WS_HANDSHAKE_ACQUIRE_TIMEOUT_S", "0.5"))  # capacity gate

    # API key for auth (required); single source: ORPHEUS_API_KEY
    api_key: str | None = os.getenv("ORPHEUS_API_KEY")
    ws_meta_keys: tuple[str, ...] = (
        "voice",
        "temperature",
        "top_p",
        "repetition_penalty",
        "trim_silence",
        "prespeech_pad_ms",
    )

    # Message schema keys
    ws_key_type: str = "type"
    ws_key_text: str = "text"
    ws_key_voice: str = "voice"
    ws_key_trim_silence: str = "trim_silence"
    ws_key_temperature: str = "temperature"
    ws_key_top_p: str = "top_p"
    ws_key_repetition_penalty: str = "repetition_penalty"
    ws_key_prespeech_pad_ms: str = "prespeech_pad_ms"
    ws_key_request_id: str = "request_id"
    ws_key_end: str = "end"
    ws_key_cancel: str = "cancel"

    # Message types
    ws_type_text: str = "text"
    ws_type_meta: str = "meta"
    ws_type_end: str = "end"
    ws_type_cancel: str = "cancel"
    ws_type_ping: str = "ping"
    ws_type_pong: str = "pong"
    ws_type_sentence: str = "sentence"
    ws_type_sentence_end: str = "sentence_end"
    ws_type_audio_end: str = "audio_end"

    # Truthy values for boolean parsing from strings
    ws_truthy_values: tuple[str, ...] = ("1", "true", "yes", "y", "on")
