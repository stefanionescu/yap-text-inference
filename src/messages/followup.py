"""Follow-up handler to continue answer after external screen analysis.

Bypasses tool routing and directly invokes the chat model with a synthetic
user utterance that embeds the analysis with a configurable prefix.
"""

from __future__ import annotations

import json
import logging
from typing import Dict, Any
from fastapi import WebSocket

from ..handlers.session_handler import session_handler
from ..persona import get_static_prefix, compose_persona_runtime
from ..execution.chat_streamer import run_chat_stream
from ..config import SCREEN_CHECKED_PREFIX


logger = logging.getLogger(__name__)


async def handle_followup_message(ws: WebSocket, msg: Dict[str, Any], session_id: str) -> None:
    """Handle 'followup' message to continue with chat-only using analysis.

    Required fields:
        - analysis_text: str

    Optional fields:
        - history_text: str (conversation history)
        - user_identity: str
        - user_utterance: str (ignored for synthesis; may be used by clients)
    """
    cfg = session_handler.get_session_config(session_id)
    if not cfg:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session; send 'start' first"}))
        return

    analysis_text = (msg.get("analysis_text") or "").strip()
    if not analysis_text:
        await ws.send_text(json.dumps({"type": "error", "message": "analysis_text is required"}))
        return

    history_text = msg.get("history_text", "")

    # Resolve persona
    if cfg["persona_text_override"]:
        static_prefix = cfg["persona_text_override"]
        runtime_text = ""
    else:
        static_prefix = get_static_prefix(
            style=cfg["persona_style"],
            gender=cfg["assistant_gender"] or "woman",
        )
        runtime_text = compose_persona_runtime(
            user_identity=msg.get("user_identity", "non-binary"),
            now_str=cfg["now_str"],
        )

    # Synthesize the follow-up prompt for the chat model
    user_utt = f"{SCREEN_CHECKED_PREFIX} {analysis_text}".strip()

    final_text = ""
    async for chunk in run_chat_stream(
        session_id=session_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
    ):
        await ws.send_text(json.dumps({"type": "token", "text": chunk}))
        final_text += chunk

    await ws.send_text(json.dumps({"type": "final", "normalized_text": final_text}))
    await ws.send_text(json.dumps({"type": "done", "usage": {}}))


