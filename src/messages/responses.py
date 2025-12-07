"""Helpers for consistent message payload shapes."""

from __future__ import annotations

from typing import Any, Mapping


def error_response(
    message: str,
    *,
    code: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a consistent error payload for websocket clients."""
    payload: dict[str, Any] = {"type": "error", "message": message}
    if code is not None:
        payload["code"] = code
    if extra:
        payload.update(extra)
    return payload







