"""Set persona message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ..utils.sanitize import sanitize_prompt
from ..handlers.session_handler import session_handler


async def handle_set_persona_message(ws: WebSocket, msg: dict, session_id: str) -> None:
    """Handle 'set_persona' message type."""
    if not session_id:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session"}))
        return

    # Runtime switch for raw persona (chat prompt)
    changed = {}

    if "chat_prompt" in msg or "persona_text" in msg:
        raw = msg.get("chat_prompt") or msg.get("persona_text")
        if raw:
            try:
                ov = sanitize_prompt(raw)
            except ValueError as e:
                await ws.send_text(json.dumps({"type": "error", "message": str(e)}))
                return
        else:
            ov = None
        changed.update(session_handler.update_session_config(session_id, persona_text_override=ov))

    # Get updated config for response
    config = session_handler.get_session_config(session_id)

    # Send ACK: persona/gender switch applied
    await ws.send_text(json.dumps({
        "type": "ack",
        "for": "set_persona",
        "ok": True,
        "session_id": session_id,
        "changed": changed,
        "assistant_gender": config.get("assistant_gender"),
        "persona_text_override": bool(config["persona_text_override"]),
    }))


