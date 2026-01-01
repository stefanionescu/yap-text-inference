"""Warm history message handler split from message_handlers for modularity."""

from fastapi import WebSocket

from ...config import DEPLOY_CHAT
from ...handlers.session.history import parse_history_messages, render_history, trim_history
from ...handlers.session.state import SessionState
from ..chat.builder import build_chat_warm_prompt
from .warm_utils import warm_chat_segment, sanitize_optional_prompt
from ...handlers.websocket.helpers import safe_send_json


async def handle_warm_history_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_history' message type.
    
    Accepts: "history": [{role: "user", content: "..."}, ...]
    """
    if not DEPLOY_CHAT:
        await safe_send_json(ws, {
            "type": "error",
            "message": "warm_history requires chat model deployment",
        })
        return
    
    # Parse and trim history
    history_messages = msg.get("history", [])
    if not isinstance(history_messages, list):
        history_messages = []
    
    # Use a temporary state for trimming
    temp_state = SessionState(session_id="warm", meta={})
    temp_state.history_turns = parse_history_messages(history_messages)
    trim_history(temp_state)
    history_text = render_history(temp_state.history_turns)

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
