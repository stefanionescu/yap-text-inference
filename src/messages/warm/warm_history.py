"""Warm history message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ...config import DEPLOY_CHAT, HISTORY_MAX_TOKENS
from ...tokens import count_tokens_chat, trim_history_preserve_messages_chat
from ...persona import build_chat_warm_prompt
from .warm_utils import warm_chat_segment


async def handle_warm_history_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_history' message type."""
    if not DEPLOY_CHAT:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "warm_history requires chat model deployment"
        }))
        return
    
    history_text = msg.get("history_text", "")
    if count_tokens_chat(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages_chat(
            history_text,
            HISTORY_MAX_TOKENS,
        )

    prompt = build_chat_warm_prompt("", "", history_text)
    await warm_chat_segment(
        ws,
        prompt=prompt,
        segment="history",
        byte_count=len(history_text),
    )


