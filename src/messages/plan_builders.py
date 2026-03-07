"""Plan-construction helpers shared by turn handlers."""

from __future__ import annotations

import uuid
from typing import Any
from src.state import TurnPlan
from src.handlers.session.manager import SessionHandler
from .start.history import resolve_history, resolve_user_utterances


def _include_latest_chat_history(state, history_turn_id: str | None) -> bool:
    """Return whether chat history selection should include the latest turn.

    The strict flow excludes the latest turn only when this request actually
    appended a chat turn. A tool-only append in mixed deployments can still
    produce a turn_id, but should not cause chat history exclusion.
    """
    if not history_turn_id:
        return True
    chat_turns = state.history_turns or []
    has_chat_turn = any(turn.turn_id == history_turn_id for turn in chat_turns)
    return not has_chat_turn


def _build_start_turn_plan(
    state,
    msg: dict[str, Any],
    cfg: dict[str, Any],
    *,
    session_handler: SessionHandler,
    sampling_overrides: dict[str, float | int | bool],
) -> TurnPlan:
    deploy_chat = session_handler.history_config.deploy_chat
    deploy_tool = session_handler.history_config.deploy_tool
    resolve_history(session_handler, state, msg)
    chat_user_utt, tool_user_utt = resolve_user_utterances(
        session_handler,
        state,
        msg.get("user_utterance", ""),
    )
    history_turn_id = session_handler.append_user_utterance(
        state,
        chat_user_utt,
        tool_user_utt=tool_user_utt,
    )
    history_turns = session_handler._history.get_turns(
        state,
        include_latest=_include_latest_chat_history(state, history_turn_id),
    )
    plan_chat_user_utt = chat_user_utt if deploy_chat else None
    static_prefix = cfg.get("chat_prompt") or ""
    return TurnPlan(
        state=state,
        request_id=f"start-{uuid.uuid4().hex}",
        static_prefix=static_prefix,
        runtime_text="",
        history_turns=history_turns,
        chat_user_utt=plan_chat_user_utt,
        tool_user_utt=tool_user_utt if deploy_tool else None,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if deploy_chat else None,
        apply_screen_checked_prefix=False,
    )


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
    history_turn_id = session_handler.append_user_utterance(
        state,
        chat_user_utt,
        tool_user_utt=tool_user_utt,
    )
    history_turns = session_handler._history.get_turns(
        state,
        include_latest=_include_latest_chat_history(state, history_turn_id),
    )
    plan_chat_user_utt = chat_user_utt if deploy_chat else None
    static_prefix = cfg.get("chat_prompt") or ""
    return TurnPlan(
        state=state,
        request_id=f"msg-{uuid.uuid4().hex}",
        static_prefix=static_prefix,
        runtime_text="",
        history_turns=history_turns,
        chat_user_utt=plan_chat_user_utt,
        tool_user_utt=tool_user_utt if deploy_tool else None,
        history_turn_id=history_turn_id,
        sampling_overrides=(sampling_overrides or None) if deploy_chat else None,
        apply_screen_checked_prefix=apply_screen_checked_prefix,
    )


__all__ = ["_build_message_turn_plan", "_build_start_turn_plan"]
