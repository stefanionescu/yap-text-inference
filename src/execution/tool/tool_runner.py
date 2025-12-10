"""Tool execution logic for processing tool calls."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from vllm.sampling_params import SamplingParams

from ...engines import get_tool_engine
from ...classifier import get_classifier_adapter
from ...config import (
    DEPLOY_DUAL,
    TOOL_MAX_OUT,
    TOOL_HISTORY_TOKENS,
    TOOL_REQUEST_PRIORITY,
    TOOL_LANGUAGE_FILTER,
    TOOL_MODEL,
    USER_UTT_MAX_TOKENS,
    is_classifier_model,
)
from ...tokens import trim_history_for_tool_sharing, trim_text_to_token_limit_tool
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
from ...utils import is_mostly_english
from .tool_filter import filter_tool_phrase

logger = logging.getLogger(__name__)

# Cache whether we're using classifier mode (checked once at startup)
_USE_CLASSIFIER: bool | None = None


def _is_classifier_mode() -> bool:
    """Check if tool model is a classifier (cached)."""
    global _USE_CLASSIFIER
    if _USE_CLASSIFIER is None:
        _USE_CLASSIFIER = is_classifier_model(TOOL_MODEL)
        if _USE_CLASSIFIER:
            logger.info("Tool runner using classifier mode (model=%s)", TOOL_MODEL)
    return _USE_CLASSIFIER


async def _run_classifier_toolcall(
    session_id: str,
    user_utt: str,
    req_id: str,
) -> dict[str, Any]:
    """Run tool call using classifier model.
    
    This is much faster than the vLLM path since it uses a lightweight
    classification model instead of an autoregressive LLM.
    
    The classifier adapter handles history formatting and trimming
    using its own tokenizer (centralized, DRY).
    """
    t0 = time.perf_counter()
    
    # Get classifier adapter (lazily initialized, has its own tokenizer)
    adapter = get_classifier_adapter()
    
    # Get raw user texts from session, let classifier trim with its tokenizer
    user_texts = session_handler.get_user_texts(session_id)
    user_history = adapter.trim_user_history(user_texts)
    
    # Run classifier
    text = adapter.run_tool_inference(user_utt, user_history)
    
    dt_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "tool_runner[classifier]: done session_id=%s req_id=%s result=%s ms=%.1f",
        session_id, req_id, text, dt_ms
    )
    
    return {"cancelled": False, "text": text}


async def _run_vllm_toolcall(
    session_id: str,
    user_utt: str,
    history_text: str,
    req_id: str,
    mark_active: bool,
) -> dict[str, Any]:
    """Run tool call using vLLM autoregressive model (original behavior)."""
    params = SamplingParams(
        temperature=TOOL_TEMPERATURE,
        top_p=TOOL_TOP_P,
        top_k=TOOL_TOP_K,
        max_tokens=TOOL_MAX_OUT,
        stop=INFERENCE_STOP,
    )
    tool_timeout_s = float(TOOL_TIMEOUT_S)
    logger.info("tool_runner[vllm]: start session_id=%s req_id=%s timeout_s=%.2f", session_id, req_id, tool_timeout_s)

    if DEPLOY_DUAL:
        tool_history = history_text
    else:
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
        logger.info("tool_runner[vllm]: timeout session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": True}

    if stream.was_cancelled:
        return {"cancelled": True}

    text = "".join(pieces).strip()
    dt_ms = (time.perf_counter() - t0) * 1000.0
    logger.info("tool_runner[vllm]: done session_id=%s req_id=%s len=%s ms=%.1f", session_id, req_id, len(text), dt_ms)
    return {"cancelled": False, "text": text}


async def run_toolcall(
    session_id: str,
    user_utt: str,
    history_text: str = "",
    request_id: str | None = None,
    mark_active: bool = True,
) -> dict[str, Any]:
    """Execute a tool call with timeout handling.
    
    Routes to either classifier or vLLM based on TOOL_MODEL type.
    """
    req_id = request_id or f"tool-{uuid.uuid4()}"

    # Phrase filter: check for known patterns FIRST to avoid model call
    # This must run before language filter to catch typos that might be misclassified as non-English
    phrase_result = filter_tool_phrase(user_utt)
    if phrase_result == "reject":
        logger.info("tool_runner: phrase filter reject session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}
    if phrase_result == "trigger":
        logger.info("tool_runner: phrase filter trigger session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "take_screenshot"}]'}

    # Language filter: skip tool call if message is not mostly English
    # Only check if phrase filter didn't match (to avoid blocking known patterns)
    if TOOL_LANGUAGE_FILTER and not is_mostly_english(user_utt):
        logger.info("tool_runner: skipped (non-English) session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}

    if mark_active:
        session_handler.set_active_request(session_id, req_id)

    # Route to classifier or vLLM based on model type
    if _is_classifier_mode():
        return await _run_classifier_toolcall(session_id, user_utt, req_id)
    else:
        return await _run_vllm_toolcall(session_id, user_utt, history_text, req_id, mark_active)
