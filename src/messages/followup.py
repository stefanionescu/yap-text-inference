"""Follow-up handler to continue answer after external screen analysis.

Bypasses tool routing and directly invokes the chat model with a synthetic
user utterance that embeds the analysis with a configurable prefix.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from fastapi import WebSocket

from ..handlers.session import session_handler
from ..execution.streaming.chat_streamer import run_chat_stream
from ..config import DEPLOY_CHAT, SCREEN_CHECKED_PREFIX, USER_UTT_MAX_TOKENS
from ..tokens import trim_text_to_token_limit_chat
from ..utils import safe_send_json


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
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "followup requires chat model deployment"
        }))
        return
    
    cfg = session_handler.get_session_config(session_id)
    if not cfg:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session; send 'start' first"}))
        return

    analysis_text = (msg.get("analysis_text") or "").strip()
    if not analysis_text:
        await ws.send_text(json.dumps({"type": "error", "message": "analysis_text is required"}))
        return

    history_text = session_handler.get_history_text(session_id)

    # Resolve persona: require session-provided chat prompt
    static_prefix = cfg.get("chat_prompt") or ""
    runtime_text = ""
    if not static_prefix:
        await ws.send_text(
            json.dumps(
                {
                    "type": "error",
                    "message": "chat_prompt must be set in session (send in start)",
                }
            )
        )
        return

    # Synthesize the follow-up prompt for the chat model
    prefixed = f"{SCREEN_CHECKED_PREFIX} {analysis_text}".strip()
    user_utt = trim_text_to_token_limit_chat(prefixed, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    # Track user utterance for pairing with assistant response later.
    # Don't re-fetch history_text - it already contains previous turns (line 50),
    # and user_utt is passed separately to the prompt builder.
    history_turn_id = session_handler.append_user_utterance(session_id, user_utt)

    final_text = ""
    sampling_overrides = cfg.get("chat_sampling")
    interrupted = False

    async for chunk in run_chat_stream(
        session_id=session_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        sampling_overrides=sampling_overrides,
    ):
        sent = await safe_send_json(ws, {"type": "token", "text": chunk})
        if not sent:
            interrupted = True
            break
        final_text += chunk

    if interrupted:
        return

    if not await safe_send_json(ws, {"type": "final", "normalized_text": final_text}):
        return
    if not await safe_send_json(ws, {"type": "done", "usage": {}}):
        return

    session_handler.append_history_turn(session_id, user_utt, final_text, turn_id=history_turn_id)


