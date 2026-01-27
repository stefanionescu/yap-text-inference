"""Follow-up handler to continue answer after external screen analysis.

Bypasses tool routing and directly invokes the chat model with a synthetic
with a screenshot analysis with a configurable prefix.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import WebSocket

from ..config import DEPLOY_CHAT
from ..handlers.session import session_handler
from ..tokens import trim_text_to_token_limit_chat
from ..execution.chat.runner import run_chat_generation
from ..handlers.websocket.helpers import safe_send_json, stream_chat_response

logger = logging.getLogger(__name__)


async def handle_followup_message(ws: WebSocket, msg: dict[str, Any], session_id: str) -> None:
    """Handle 'followup' message to continue with chat-only using analysis.

    Required fields:
        - analysis_text: str

    Optional fields:
        - user_identity: str
        - user_utterance: str (ignored for synthesis; may be used by clients)
    """
    if not DEPLOY_CHAT:
        await safe_send_json(ws, {"type": "error", "message": "followup requires chat model deployment"})
        return
    
    cfg = session_handler.get_session_config(session_id)
    if not cfg:
        await safe_send_json(ws, {"type": "error", "message": "no active session; send 'start' first"})
        return

    analysis_text = (msg.get("analysis_text") or "").strip()
    if not analysis_text:
        await safe_send_json(ws, {"type": "error", "message": "analysis_text is required"})
        return

    history_text = session_handler.get_history_text(session_id)

    # Resolve persona: require session-provided chat prompt
    static_prefix = cfg.get("chat_prompt") or ""
    runtime_text = ""
    if not static_prefix:
        await safe_send_json(ws, {"type": "error", "message": "chat_prompt must be set in session (send in start)"})
        return

    # Synthesize the follow-up prompt for the chat model
    prefix = session_handler.get_screen_checked_prefix(session_id)
    # Trim analysis_text to fit within budget after prefix is added
    effective_max = session_handler.get_effective_user_utt_max_tokens(
        session_id, for_followup=True
    )
    trimmed_analysis = trim_text_to_token_limit_chat(
        analysis_text, max_tokens=effective_max, keep="start"
    )
    user_utt = f"{prefix} {trimmed_analysis}".strip()
    # Track user utterance for pairing with assistant response later.
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)

    sampling_overrides = cfg.get("chat_sampling")

    await stream_chat_response(
        ws,
        run_chat_generation(
            session_id=session_id,
            static_prefix=static_prefix,
            runtime_text=runtime_text,
            history_text=history_text,
            user_utt=user_utt,
            sampling_overrides=sampling_overrides,
        ),
        session_id,
        user_utt,
        history_turn_id=history_turn_id,
        history_user_utt=trimmed_analysis,
    )
