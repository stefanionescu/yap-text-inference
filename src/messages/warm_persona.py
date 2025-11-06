"""Warm persona message handler split from message_handlers for modularity."""

import json
import uuid
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..engines import get_chat_engine
from ..utils.sanitize import sanitize_prompt


async def handle_warm_persona_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_persona' message type."""
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

    warm_prompt = f"<|persona|>\n{static_prefix.strip()}\n<|assistant|>\n"
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    req_id = f"warm-p-{uuid.uuid4()}"

    stream = (await get_chat_engine()).generate(
        prompt=warm_prompt,
        sampling_params=params,
        request_id=req_id,
        priority=1,
    )
    async for _ in stream:
        break

    await ws.send_text(json.dumps({
        "type": "warmed",
        "segment": "persona_static",
        "bytes": len(static_prefix)
    }))


