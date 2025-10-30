"""Warm persona message handler split from message_handlers for modularity."""

import json
import uuid
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..engines import get_chat_engine
from ..persona import get_static_prefix
from ..utils.validation import normalize_gender


async def handle_warm_persona_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_persona' message type."""
    # Warm the STATIC PREFIX only for a given style/gender (prefix sharing)
    persona_override = msg.get("persona_text")
    if persona_override:
        static_prefix = persona_override
    else:
        gender = normalize_gender(msg.get("assistant_gender")) or "woman"
        static_prefix = get_static_prefix(
            style=msg.get("persona_style", "wholesome"),
            gender=gender,
        )

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


