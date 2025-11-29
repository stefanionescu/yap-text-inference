"""Tool execution logic for processing tool calls."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from vllm.sampling_params import SamplingParams

from ...engines import get_tool_engine
from ...config import TOOL_MAX_OUT, TOOL_HISTORY_TOKENS, TOOL_REQUEST_PRIORITY
from ...tokens import trim_history_for_tool_sharing, trim_text_to_token_limit_tool
from ...config import USER_UTT_MAX_TOKENS
from ...handlers.session import session_handler
from ...config.sampling import (
    TOOL_TEMPERATURE,
    TOOL_TOP_P,
    TOOL_TOP_K,
    INFERENCE_STOP,
)
from ...config.timeouts import TOOL_TIMEOUT_S
from ..streaming.llm_stream import LLMStream, LLMStreamConfig
from ...tokens.prompt_cache import compile_tool_prompt

logger = logging.getLogger(__name__)


async def run_toolcall(
    session_id: str,
    user_utt: str,
    history_text: str = "",
    request_id: str | None = None,
    mark_active: bool = True,
) -> dict[str, Any]:
    """Execute a tool call with timeout handling and KV cache sharing."""
    req_id = request_id or f"tool-{uuid.uuid4()}"

    if mark_active:
        session_handler.set_active_request(session_id, req_id)

    params = SamplingParams(
        temperature=TOOL_TEMPERATURE,
        top_p=TOOL_TOP_P,
        top_k=TOOL_TOP_K,
        max_tokens=TOOL_MAX_OUT,
        stop=INFERENCE_STOP,
    )
    tool_timeout_s = float(TOOL_TIMEOUT_S)
    logger.info("tool_runner: start session_id=%s req_id=%s timeout_s=%.2f", session_id, req_id, tool_timeout_s)

    tool_history = trim_history_for_tool_sharing(history_text, TOOL_HISTORY_TOKENS)
    cfg = session_handler.get_session_config(session_id)
    base_tool_prompt = cfg.get("tool_prompt")
    if not base_tool_prompt:
        raise RuntimeError("tool_prompt not set for session")
    tool_user_utt = trim_text_to_token_limit_tool(user_utt, max_tokens=USER_UTT_MAX_TOKENS, keep="start")
    compiled_prompt = compile_tool_prompt(base_tool_prompt, tool_user_utt, tool_history)

    stream = LLMStream(
        LLMStreamConfig(
            name="tool",
            session_id=session_id,
            request_id=req_id,
            prompt=compiled_prompt.text,
            sampling_params=params,
            engine_getter=get_tool_engine,
            timeout_s=tool_timeout_s,
            priority=TOOL_REQUEST_PRIORITY,
            flush_ms=0.0,
            cancel_check=(
                (lambda: session_handler.is_request_cancelled(session_id, req_id))
                if mark_active
                else None
            ),
        )
    )

    pieces: list[str] = []
    t0 = time.perf_counter()
    try:
        async for chunk in stream:
            pieces.append(chunk)
    except asyncio.TimeoutError:
        logger.info("tool_runner: timeout session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": True}

    if stream.was_cancelled:
        return {"cancelled": True}

    text = "".join(pieces).strip()
    dt_ms = (time.perf_counter() - t0) * 1000.0
    logger.info("tool_runner: done session_id=%s req_id=%s len=%s ms=%.1f", session_id, req_id, len(text), dt_ms)
    return {"cancelled": False, "text": text}
