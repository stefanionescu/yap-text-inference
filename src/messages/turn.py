"""Unified turn handler for both ``start`` and ``message`` payloads."""

from __future__ import annotations

from fastapi import WebSocket
from typing import Any, Literal
from .dispatch import dispatch_execution
from src.runtime.dependencies import RuntimeDeps
from src.handlers.session.manager import SessionHandler
from .message import plan_message_turn as _plan_message_turn
from .start import bootstrap_start_turn as _bootstrap_start_turn
from src.handlers.websocket.supervision import spawn_session_task


async def handle_turn_message(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    msg_type: Literal["start", "message"],
    session_handler: SessionHandler,
    runtime_deps: RuntimeDeps,
) -> bool:
    """Handle one session turn message by planning + dispatching execution."""
    if msg_type == "start":
        return await _bootstrap_start_turn(ws, msg, state, session_handler=session_handler)

    plan = await _plan_message_turn(ws, msg, state, session_handler=session_handler)
    if plan is None:
        return False

    await spawn_session_task(
        ws,
        state,
        request_id=plan.request_id,
        operation=dispatch_execution(ws, plan, runtime_deps),
        session_handler=session_handler,
    )
    return True


__all__ = ["handle_turn_message"]
