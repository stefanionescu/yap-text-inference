"""Warm history message handler split from message_handlers for modularity."""

import json
import uuid
from fastapi import WebSocket
from vllm.sampling_params import SamplingParams

from ..engines import get_chat_engine
from ..config import HISTORY_MAX_TOKENS
from ..tokens import count_tokens, trim_history_preserve_messages


async def handle_warm_history_message(ws: WebSocket, msg: dict) -> None:
    """Handle 'warm_history' message type."""
    history_text = msg.get("history_text", "")
    if count_tokens(history_text) > HISTORY_MAX_TOKENS:
        history_text = trim_history_preserve_messages(
            history_text,
            HISTORY_MAX_TOKENS,
        )

    warm_prompt = f"<|history|>\n{history_text.strip()}\n<|assistant|>\n"
    params = SamplingParams(temperature=0.0, max_tokens=1, stop=["<|end|>", "</s>"])
    req_id = f"warm-h-{uuid.uuid4()}"

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
        "segment": "history",
        "bytes": len(history_text)
    }))


