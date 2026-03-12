"""Plan-construction helpers shared by message handlers."""

from __future__ import annotations

import uuid
from typing import Any
from src.state import TurnPlan
from src.handlers.session.manager import SessionHandler
from .start.history import resolve_user_utterances


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
        for_followup=apply_screen_checked_prefix,
    )
    history_turn_id = session_handler.reserve_history_turn_id(
        state,
        chat_user_utt,
        tool_user_utt=tool_user_utt,
    )
    history_messages = session_handler._history.get_chat_messages(state)
    plan_chat_user_utt = chat_user_utt if deploy_chat else None
    static_prefix = cfg.get("chat_prompt") or ""
    return TurnPlan(
        state=state,
        request_id=f"msg-{uuid.uuid4().hex}",
        static_prefix=static_prefix,
        runtime_text="",
        history_messages=history_messages,
        chat_user_utt=plan_chat_user_utt,
        tool_user_utt=tool_user_utt if deploy_tool else None,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if deploy_chat else None,
        apply_screen_checked_prefix=apply_screen_checked_prefix,
    )


__all__ = ["_build_message_turn_plan"]
