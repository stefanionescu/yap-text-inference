"""Warm persona message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ...config import DEPLOY_CHAT
from ..sanitize.prompt_sanitizer import sanitize_prompt
from ...helpers.prompts import build_chat_warm_prompt
from .warm_utils import warm_chat_segment


async def handle_warm_persona_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_persona' message type."""
    if not DEPLOY_CHAT:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "warm_persona requires chat model deployment"
        }))
        return
    
    # Warm the STATIC PREFIX using client-provided chat prompt
    raw_prompt = msg.get("chat_prompt")
    if not raw_prompt:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "chat_prompt is required to warm persona"
        }))
        return
    try:
        static_prefix = sanitize_prompt(raw_prompt)
    except ValueError as e:
        await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
        return

    prompt = build_chat_warm_prompt(static_prefix, "", "")
    await warm_chat_segment(
        ws,
        prompt=prompt,
        segment="persona_static",
        byte_count=len(static_prefix),
    )


