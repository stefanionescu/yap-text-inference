"""Tool execution logic for processing tool calls."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from ...classifier import get_classifier_adapter
from ...config import TOOL_LANGUAGE_FILTER
from ...handlers.session import session_handler
from ...utils import is_mostly_english
from .filter import filter_tool_phrase

logger = logging.getLogger(__name__)

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
    
    # Snapshot trimmed user-only history (most recent last, already token-limited)
    tool_history = session_handler.get_tool_history_text(session_id)

    def _classify_sync() -> str:
        """Run classifier inference in a worker thread."""
        return adapter.run_tool_inference(user_utt, tool_history)

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _classify_sync)
    
    dt_ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "tool_runner[classifier]: done session_id=%s req_id=%s result=%s ms=%.1f",
        session_id, req_id, text, dt_ms
    )
    
    return {"cancelled": False, "text": text}


async def run_toolcall(
    session_id: str,
    user_utt: str,
    history_text: str = "",
    request_id: str | None = None,
    mark_active: bool = True,
) -> dict[str, Any]:
    """Execute a tool call with timeout handling using the classifier adapter."""
    req_id = request_id or f"tool-{uuid.uuid4()}"

    # Phrase filter: check for known patterns FIRST to avoid model call
    # This must run before language filter to catch typos that might be misclassified as non-English
    phrase_result = filter_tool_phrase(user_utt)
    if phrase_result == "no_screenshot":
        logger.info("tool_runner: phrase filter no_screenshot session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}
    if phrase_result == "take_screenshot":
        logger.info("tool_runner: phrase filter take_screenshot session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "take_screenshot"}]'}
    if phrase_result == "start_freestyle":
        logger.info("tool_runner: phrase filter start_freestyle session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "start_freestyle"}]'}
    if phrase_result == "stop_freestyle":
        logger.info("tool_runner: phrase filter stop_freestyle session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "stop_freestyle"}]'}
    if phrase_result == "switch_gender_male":
        logger.info("tool_runner: phrase filter switch_gender_male session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "switch_gender", "param": "male"}]'}
    if phrase_result == "switch_gender_female":
        logger.info("tool_runner: phrase filter switch_gender_female session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "switch_gender", "param": "female"}]'}

    # Language filter: skip tool call if message is not mostly English
    # Only check if phrase filter didn't match (to avoid blocking known patterns)
    if TOOL_LANGUAGE_FILTER and not is_mostly_english(user_utt):
        logger.info("tool_runner: skipped (non-English) session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}

    if mark_active:
        session_handler.set_active_request(session_id, req_id)

    # Route to classifier
    return await _run_classifier_toolcall(session_id, user_utt, req_id)
