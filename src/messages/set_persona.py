"""Set persona message handler split from message_handlers for modularity."""

import json
from fastapi import WebSocket

from ..utils.validation import (
    normalize_gender, validate_persona_style, ALLOWED_PERSONALITIES,
)
from ..handlers.session_handler import session_handler


async def handle_set_persona_message(ws: WebSocket, msg: dict, session_id: str) -> None:
    """Handle 'set_persona' message type."""
    if not session_id:
        await ws.send_text(json.dumps({"type": "error", "message": "no active session"}))
        return

    # Runtime switch for assistant gender / style / raw persona
    changed = {}

    g = normalize_gender(msg.get("assistant_gender"))
    if g is not None:
        changed.update(session_handler.update_session_config(session_id, assistant_gender=g))

    if "persona_style" in msg and msg["persona_style"]:
        style = msg["persona_style"].strip()
        if not validate_persona_style(style):
            await ws.send_text(json.dumps({
                "type": "error",
                "message": f"invalid persona_style '{style}'; allowed: {sorted(ALLOWED_PERSONALITIES)}"
            }))
            return
        changed.update(session_handler.update_session_config(session_id, persona_style=style))

    if "persona_text" in msg:
        # explicit None/empty clears the override
        ov = msg.get("persona_text") or None
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
        "assistant_gender": config["assistant_gender"],
        "persona_style": config["persona_style"],
        "persona_text_override": bool(config["persona_text_override"]),
    }))


