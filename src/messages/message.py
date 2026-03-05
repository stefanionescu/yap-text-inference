"""Message handler for subsequent conversation turns.

This module handles the 'message' WebSocket message type, which continues
an existing conversation session. Unlike 'start', it does not accept
history or persona configuration — those are locked in at session creation.

The handler validates the user utterance, updates sampling if provided,
appends to history, and dispatches execution as a background task.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from fastapi import WebSocket
from src.state import StartPlan
from .validators import ValidationError
from src.state.session import SessionState
from .start.dispatch import dispatch_execution
from .start.history import trim_user_utterance
from src.runtime.dependencies import RuntimeDeps
from ..handlers.websocket.errors import send_error
from .start.sampling import extract_sampling_overrides
from src.handlers.session.manager import SessionHandler
from ..config.websocket import WS_ERROR_INVALID_MESSAGE, WS_ERROR_INVALID_PAYLOAD

logger = logging.getLogger(__name__)


async def _validate_message_fields(
    ws: WebSocket,
    msg: dict[str, Any],
    state: SessionState,
    *,
    session_handler: SessionHandler,
) -> tuple[str, dict[str, Any], dict[str, Any] | None] | None:
    """Validate utterance, session config, and sampling; return None on error."""
    user_utt = (msg.get("user_utterance") or "").strip()
    if not user_utt:
        await send_error(
            ws,
            code=WS_ERROR_INVALID_PAYLOAD,
            message="user_utterance is required",
        )
        return None

    cfg = session_handler.get_session_config(state)
    if not cfg:
        await send_error(
            ws,
            code=WS_ERROR_INVALID_MESSAGE,
            message="no active session; send 'start' first",
        )
        return None

    try:
        sampling_overrides = extract_sampling_overrides(msg)
    except ValidationError as err:
        await send_error(
            ws,
            code=WS_ERROR_INVALID_PAYLOAD,
            message=err.message,
        )
        await ws.close(code=1008)
        return None

    return user_utt, cfg, sampling_overrides


async def handle_message_message(
    ws: WebSocket,
    msg: dict[str, Any],
    state: SessionState,
    *,
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> None:
    """Handle 'message' type for subsequent conversation turns."""
    result = await _validate_message_fields(
        ws,
        msg,
        state,
        session_handler=session_handler,
    )
    if result is None:
        return
    user_utt, cfg, sampling_overrides = result

    if sampling_overrides:
        session_handler.update_session_config(state, chat_sampling=sampling_overrides)

    history_text = session_handler.get_history_text(state)
    trimmed_utt = trim_user_utterance(session_handler, state, user_utt)
    history_turn_id = session_handler.append_user_utterance(state, trimmed_utt)

    static_prefix = cfg.get("chat_prompt") or ""
    plan = StartPlan(
        state=state,
        request_id=f"msg-{id(state)}-{asyncio.get_event_loop().time():.0f}",
        static_prefix=static_prefix,
        runtime_text="",
        history_text=history_text,
        user_utt=trimmed_utt,
        history_turn_id=history_turn_id,
        sampling_overrides=sampling_overrides or None,
    )

    task = asyncio.create_task(dispatch_execution(ws, plan, runtime_deps))
    session_handler.track_task(state, task)


__all__ = ["handle_message_message"]
