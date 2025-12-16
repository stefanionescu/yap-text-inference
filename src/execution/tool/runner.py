"""Tool execution logic for processing tool calls.

This module runs the tool/intent classification pipeline that determines
whether a user message requires special handling (screenshot, control commands).

Pipeline:
    1. Phrase Filter: Check for exact pattern matches (fast, regex-based)
       - Freestyle commands (start/stop)
       - Gender switches
       - Personality switches
       - Screenshot triggers
       
    2. Language Filter: Skip non-English messages (optional)
       - Uses lingua library for language detection
       - Avoids false positives from non-English text
       
    3. Classifier Model: Run lightweight classification model
       - BERT-style sequence classifier
       - Returns tool name or empty array

The phrase filter runs first to short-circuit common commands without
invoking the model. This improves latency for known patterns.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from ...classifier import get_classifier_adapter
from ...config import TOOL_LANGUAGE_FILTER
from ...handlers.session import session_handler
from .filter import filter_tool_phrase
from .language import is_mostly_english

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
    """Execute tool classification pipeline.
    
    Runs the full tool detection pipeline:
    1. Phrase filter for known patterns
    2. Language filter for non-English
    3. Classifier model for intent detection
    
    Args:
        session_id: Session for history lookup and request tracking.
        user_utt: User message to classify.
        history_text: Conversation history (unused, kept for compatibility).
        request_id: Optional request ID for tracking.
        mark_active: Whether to mark this as the active request.
        
    Returns:
        Dict with keys:
        - cancelled: bool (False unless interrupted)
        - text: JSON string of tool array, e.g. '[{"name": "take_screenshot"}]'
        - timeout: bool (only if timed out)
    """
    req_id = request_id or f"tool-{uuid.uuid4()}"

    # Get session personalities for personality switch detection
    personalities = session_handler.get_personalities(session_id)

    # Phrase filter: check for known patterns FIRST to avoid model call
    # This must run before language filter to catch typos that might be misclassified as non-English
    phrase_result = filter_tool_phrase(user_utt, personalities)
    action = phrase_result.action
    
    if action == "no_screenshot":
        logger.info("tool_runner: phrase filter no_screenshot session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}
    if action == "take_screenshot":
        logger.info("tool_runner: phrase filter take_screenshot session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "take_screenshot"}]'}
    if action == "start_freestyle":
        logger.info("tool_runner: phrase filter start_freestyle session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "start_freestyle"}]'}
    if action == "stop_freestyle":
        logger.info("tool_runner: phrase filter stop_freestyle session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": '[{"name": "stop_freestyle"}]'}
    if action == "switch_gender":
        gender = phrase_result.param  # "male" or "female"
        logger.info("tool_runner: phrase filter switch_gender=%s session_id=%s req_id=%s", gender, session_id, req_id)
        result = [{"name": "switch_gender", "params": [gender]}]
        return {"cancelled": False, "text": json.dumps(result)}
    if action == "switch_personality":
        personality_name = phrase_result.param
        logger.info(
            "tool_runner: phrase filter switch_personality=%s session_id=%s req_id=%s",
            personality_name, session_id, req_id
        )
        result = [{"name": "switch_personality", "params": [personality_name]}]
        return {"cancelled": False, "text": json.dumps(result)}
    if action == "switch_gender_and_personality":
        gender = phrase_result.param  # "male" or "female"
        personality_name = phrase_result.param2
        logger.info(
            "tool_runner: phrase filter switch_gender_and_personality gender=%s personality=%s session_id=%s req_id=%s",
            gender, personality_name, session_id, req_id
        )
        result = [{"name": "switch_gender_and_personality", "params": [gender, personality_name]}]
        return {"cancelled": False, "text": json.dumps(result)}

    # Language filter: skip tool call if message is not mostly English
    # Only check if phrase filter didn't match (to avoid blocking known patterns)
    if TOOL_LANGUAGE_FILTER and not is_mostly_english(user_utt):
        logger.info("tool_runner: skipped (non-English) session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}

    if mark_active:
        session_handler.set_active_request(session_id, req_id)

    # Route to classifier
    return await _run_classifier_toolcall(session_id, user_utt, req_id)
