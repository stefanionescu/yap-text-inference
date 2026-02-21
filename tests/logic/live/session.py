"""Live session payload builders.

This module keeps payload construction in the logic layer so `tests.state`
remains a pure dataclass package without websocket helper dependencies.
"""

from __future__ import annotations

from typing import Any
from tests.state.live import LiveSession
from tests.state.metrics import SessionContext
from tests.helpers.websocket.payloads import (
    build_start_payload as build_ws_start_payload,
    build_message_payload as build_ws_message_payload,
)


def build_start_payload(session: LiveSession, user_text: str) -> dict[str, Any]:
    """Build the start payload for a live session turn."""
    ctx = SessionContext(
        session_id=session.session_id,
        gender=session.persona.gender,
        personality=session.persona.personality,
        chat_prompt=session.persona.prompt,
        sampling=session.sampling,
    )
    payload = build_ws_start_payload(ctx, user_text, history=session.history)
    session._started = True
    return payload


def build_message_payload(session: LiveSession, user_text: str) -> dict[str, Any]:
    """Build the message payload for subsequent live session turns."""
    return build_ws_message_payload(
        session.session_id,
        user_text,
        sampling=session.sampling,
    )


__all__ = ["build_message_payload", "build_start_payload"]
