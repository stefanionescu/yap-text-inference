"""WebSocket helper utilities for authorization, closing, and message handling."""

import asyncio

from fastapi import WebSocket

from server.auth.utils import extract_api_key_from_ws, is_api_key_authorized
from server.config import settings


async def safe_ws_close(ws: WebSocket, code: int | None = None) -> None:
    """Close a websocket without raising and ignore double-close."""
    import contextlib

    with contextlib.suppress(Exception):
        if code is not None:
            await ws.close(code=code)
        else:
            await ws.close()


async def authorize_ws(ws: WebSocket) -> bool:
    """Authorize a websocket connection via API key (headers or query)."""
    provided_key = extract_api_key_from_ws(ws)
    return is_api_key_authorized(provided_key)


async def purge_text_messages(message_queue: asyncio.Queue[dict | None]) -> None:
    """Remove queued text messages; keep non-text in original order."""
    kept: list[dict] = []
    while True:
        try:
            item = message_queue.get_nowait()
        except asyncio.QueueEmpty:
            break
        if not item:
            continue
        if item.get(settings.ws_key_type) == settings.ws_type_text:
            continue
        kept.append(item)
    for item in kept:
        await message_queue.put(item)


def apply_sampling_overrides(base_kwargs: dict, message: dict) -> dict:
    """
    Apply per-message overrides onto a sampling kwargs dict (non-destructive).

    Precedence:
    1. Server defaults (already baked into `base_kwargs`).
    2. Connection-level metadata (also baked into `base_kwargs`).
    3. Per-message overrides (applied here if present).
    """
    sampling_kwargs = dict(base_kwargs)
    import contextlib

    if settings.ws_key_temperature in message:
        with contextlib.suppress(Exception):
            sampling_kwargs["temperature"] = float(message[settings.ws_key_temperature])
    if settings.ws_key_top_p in message:
        with contextlib.suppress(Exception):
            sampling_kwargs["top_p"] = float(message[settings.ws_key_top_p])
    if settings.ws_key_repetition_penalty in message:
        with contextlib.suppress(Exception):
            sampling_kwargs["repetition_penalty"] = float(message[settings.ws_key_repetition_penalty])
    return sampling_kwargs


def parse_trim_silence_override(message: dict, default_flag: bool) -> bool:
    """
    Parse optional trim_silence override.

    Message-level overrides win; otherwise fall back to the connection default.
    """
    if settings.ws_key_trim_silence not in message:
        return default_flag

    try:
        val = message[settings.ws_key_trim_silence]
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.strip().lower() in set(settings.ws_truthy_values)
        return bool(int(val))
    except Exception:
        return default_flag


def parse_prespeech_pad_override(message: dict, default_ms: float) -> float:
    """
    Parse optional prespeech_pad_ms override, clamped and validated; else return default.

    Orders of precedence: per-message override > connection meta > server default.
    Accepts numeric or string input and clamps to configured min/max bounds.
    """
    if settings.ws_key_prespeech_pad_ms not in message:
        return default_ms
    try:
        value = float(message[settings.ws_key_prespeech_pad_ms])
        low = float(settings.silence_prespeech_min_ms)
        high = float(settings.silence_prespeech_max_ms)
        if value < low:
            return low
        if value > high:
            return high
        return value
    except Exception:
        return default_ms
