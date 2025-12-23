"""Shared test helpers covering handshake auth, connection URLs, and defaults."""

from __future__ import annotations

import contextlib
import inspect
import ipaddress
from typing import Any
from urllib.parse import urlparse, urlunparse

from tests.config.audio import DEFAULT_SAMPLE_RATE as _DEFAULT_SAMPLE_RATE  # noqa: E402
from tests.config.network import (  # noqa: E402
    HTTP_PORT,
    INTERNAL_SUFFIXES,
    LOCAL_HOSTNAMES,
    TLS_PORT,
    WS_BUSY_CLOSE_CODE,
)
from tests.config.streaming import END_SENTINEL  # noqa: E402, F401
from tests.config.text import DEFAULT_TEXT  # noqa: E402

DEFAULT_SAMPLE_RATE = _DEFAULT_SAMPLE_RATE


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    return s in {"1", "true", "yes", "y", "on"}


def should_use_tls(host: str) -> bool:
    """Heuristic: choose TLS (wss) for public hosts by default.

    Rules:
    - Explicit port 443 -> TLS; port 80 -> non-TLS.
    - Local/loopback/private IPs and localhost -> non-TLS.
    - Everything else (public-looking hostnames) -> TLS.
    """
    raw = (host or "").strip()
    if not raw:
        return False

    parsed = urlparse(raw if "://" in raw else f"scheme://{raw}")
    hostname = (parsed.hostname or "").lower()
    port = parsed.port

    if port == TLS_PORT:
        return True
    if port == HTTP_PORT:
        return False

    should_tls = True
    if hostname in LOCAL_HOSTNAMES or _is_private_ip(hostname) or hostname.endswith(INTERNAL_SUFFIXES):
        should_tls = False

    return should_tls


def ws_tts_url(server: str) -> str:
    raw = (server or "").strip().strip("/")
    if raw.startswith("http://"):
        s = "ws://" + raw[len("http://") :]
    elif raw.startswith("https://"):
        s = "wss://" + raw[len("https://") :]
    elif raw.startswith(("ws://", "wss://")):
        s = raw
    else:
        use_tls = should_use_tls(raw)
        scheme = "wss" if use_tls else "ws"
        s = f"{scheme}://{raw}"
    parsed = urlparse(s)
    path = (parsed.path or "").rstrip("/") + "/ws/tts"
    return urlunparse((parsed.scheme, parsed.netloc, path, "", parsed.query, ""))


def build_server_base(server: str | None, host: str, port: int, secure: bool) -> str:
    server_str = (server or "").strip().strip("/")
    if server_str:
        return server_str
    host = (host or "127.0.0.1").strip().strip("/")
    use_tls = secure or should_use_tls(host)
    scheme = "wss" if use_tls else "ws"
    netloc = host if (":" in host) else f"{host}:{port}"
    return f"{scheme}://{netloc}"


def auth_headers(api_key: str | None) -> dict[str, str]:
    token = (api_key or "").strip()
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


def websocket_connect_kwargs(api_key: str | None, *, max_size: int | None = None) -> dict[str, Any]:
    """Build kwargs for websockets.connect with Authorization headers."""
    kwargs: dict[str, Any] = {"max_size": max_size}
    headers = auth_headers(api_key)
    if headers:
        kwargs[choose_headers_kwarg()] = headers
    return kwargs


def choose_headers_kwarg() -> str:
    try:
        import websockets

        sig = inspect.signature(websockets.connect)
        params = sig.parameters
        if "extra_headers" in params:
            return "extra_headers"
        if "additional_headers" in params:
            return "additional_headers"
    except Exception:
        return "extra_headers"
    return "extra_headers"


def build_meta(
    voice: str,
    trim_silence: bool,
    temperature: float | None = None,
    top_p: float | None = None,
    repetition_penalty: float | None = None,
    prespeech_pad_ms: float | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"voice": voice, "trim_silence": bool(trim_silence)}
    if temperature is not None:
        meta["temperature"] = temperature
    if top_p is not None:
        meta["top_p"] = top_p
    if repetition_penalty is not None:
        meta["repetition_penalty"] = repetition_penalty
    if prespeech_pad_ms is not None:
        meta["prespeech_pad_ms"] = prespeech_pad_ms
    return meta


def load_texts(inline_texts: list[str] | None, default_text: str = DEFAULT_TEXT) -> list[str]:
    if inline_texts:
        return [t for t in inline_texts if t and str(t).strip()]
    return [default_text]


def is_busy_error(exc: Exception) -> bool:
    """Detect server-at-capacity errors (WebSocket close code 1013 or similar messages)."""
    with contextlib.suppress(Exception):
        code = getattr(exc, "code", None)
        if code == WS_BUSY_CLOSE_CODE:
            return True
    text = f"{type(exc).__name__}:{exc}"
    lt = text.lower()
    return ("1013" in text) or ("busy" in lt) or ("no space" in lt) or ("try again later" in lt)


def _is_private_ip(hostname: str) -> bool:
    try:
        ip_obj = ipaddress.ip_address(hostname)
        return ip_obj.is_loopback or ip_obj.is_private or ip_obj.is_link_local
    except ValueError:
        return False
