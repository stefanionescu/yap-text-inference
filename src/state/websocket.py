"""WebSocket-related dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _ChatStreamState:
    """Internal state for stream_chat_response."""

    final_text: str
    text_visible: bool
    session_id: str
    request_id: str
    interrupted: bool = False


__all__ = ["_ChatStreamState"]
