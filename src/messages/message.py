"""Message-turn planning for follow-up user utterances."""

from __future__ import annotations

import copy
import time
import uuid
from typing import Any
from fastapi import WebSocket
from src.state import TurnPlan
from .validators import ValidationError
from .history import resolve_user_utterances
from .sampling import extract_sampling_overrides
from src.handlers.websocket.errors import send_error
from src.handlers.session.manager import SessionHandler
from src.handlers.session.config import update_session_config
from src.telemetry.phases import record_phase_error, record_phase_latency
from src.config.websocket import WS_ERROR_INVALID_MESSAGE, WS_ERROR_INVALID_PAYLOAD


async def _send_turn_error(ws: WebSocket, *, code: str, message: str, close: bool = False) -> None:
    await send_error(ws, code=code, message=message)
    if close:
        await ws.close(code=1008)


def _build_message_turn_plan(
    state,
    cfg: dict[str, Any],
    incoming_user_utt: str,
    *,
    deploy_chat: bool,
    deploy_tool: bool,
    session_handler: SessionHandler,
    sampling_overrides: dict[str, Any],
) -> TurnPlan:
    apply_screen_checked_prefix = bool(state.screen_followup_pending)
    chat_user_utt, tool_user_utt = resolve_user_utterances(
        session_handler,
        state,
        incoming_user_utt,
    )
    history_turn_id = session_handler.reserve_history_turn_id(
        state,
        chat_user_utt,
        tool_user_utt=tool_user_utt,
    )
    history_messages = session_handler.get_chat_messages(state)
    return TurnPlan(
        state=state,
        request_id=f"msg-{uuid.uuid4().hex}",
        static_prefix=cfg.get("chat_prompt") or "",
        runtime_text="",
        history_messages=history_messages,
        deploy_chat=deploy_chat,
        deploy_tool=deploy_tool,
        chat_user_utt=chat_user_utt if deploy_chat else None,
        tool_user_utt=tool_user_utt if deploy_tool else None,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if deploy_chat else None,
        apply_screen_checked_prefix=apply_screen_checked_prefix,
    )


async def plan_message_turn(
    ws: WebSocket,
    msg: dict[str, Any],
    state,
    *,
    session_handler: SessionHandler,
) -> TurnPlan | None:
    """Build a validated turn plan from a follow-up message payload."""
    t0 = time.perf_counter()
    try:
        deploy_chat = session_handler.history_config.deploy_chat
        deploy_tool = session_handler.history_config.deploy_tool
        incoming_user_utt = (msg.get("user_utterance") or "").strip()
        if not incoming_user_utt:
            record_phase_error("validate", "missing_user_utterance")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_PAYLOAD, message="user_utterance is required")
            return None

        cfg = copy.deepcopy(state.meta)
        if not cfg:
            record_phase_error("validate", "missing_session")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_MESSAGE, message="no active session; send 'start' first")
            return None

        try:
            sampling_overrides = extract_sampling_overrides(msg, deploy_chat=deploy_chat)
        except ValidationError as err:
            record_phase_error("validate", "invalid_sampling")
            await _send_turn_error(ws, code=WS_ERROR_INVALID_PAYLOAD, message=err.message, close=True)
            return None

        if sampling_overrides:
            update_session_config(
                state,
                count_prefix_tokens_fn=session_handler.count_prefix_tokens,
                chat_sampling=sampling_overrides,
            )

        return _build_message_turn_plan(
            state,
            cfg,
            incoming_user_utt,
            deploy_chat=deploy_chat,
            deploy_tool=deploy_tool,
            session_handler=session_handler,
            sampling_overrides=sampling_overrides,
        )
    finally:
        record_phase_latency("validate", time.perf_counter() - t0)


__all__ = ["plan_message_turn"]
