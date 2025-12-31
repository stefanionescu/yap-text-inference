"""Warm history message handler split from message_handlers for modularity."""

from fastapi import WebSocket

from ...config import DEPLOY_CHAT, HISTORY_MAX_TOKENS
from ...tokens import count_tokens_chat, trim_history_preserve_messages_chat
from ..chat.builder import build_chat_warm_prompt
from .warm_utils import warm_chat_segment, sanitize_optional_prompt
from ...handlers.websocket.helpers import safe_send_json


async def handle_warm_history_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_history' message type."""
    if not DEPLOY_CHAT:
        await safe_send_json(ws, {
            "type": "error",
            "message": "warm_history requires chat model deployment",
        })
        return
    
    history_text = msg.get("history_text", "")
    if count_tokens_chat(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages_chat(
            history_text,
            HISTORY_MAX_TOKENS,
        )

    try:
        # Optional persona/runtime so cache warmup matches real prompts
        static_prefix = sanitize_optional_prompt(msg.get("chat_prompt") or msg.get("persona_text"))
        runtime_text = sanitize_optional_prompt(msg.get("runtime_text"))
    except ValueError as e:
        await safe_send_json(ws, {
            "type": "error",
            "message": str(e),
        })
        return

    prompt = build_chat_warm_prompt(static_prefix, runtime_text, history_text)
    await warm_chat_segment(
        ws,
        prompt=prompt,
        segment="history",
        byte_count=len(history_text) + len(static_prefix) + len(runtime_text),
    )
