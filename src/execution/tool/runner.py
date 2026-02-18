"""Tool execution logic for processing tool calls.

This module runs the tool/intent classification pipeline that determines
whether a user message requires special handling (screenshot, control commands).

Pipeline:
    1. Language Filter: Skip non-English messages (optional)
       - Uses lingua library for language detection
       - Avoids false positives from non-English text

    2. Classifier Model: Run lightweight classification model
       - BERT-style sequence classifier
       - Returns tool name or empty array
"""

from __future__ import annotations

import time
import uuid
import asyncio
import logging
from typing import Any

from src.telemetry.sentry import add_breadcrumb
from src.telemetry.instruments import get_metrics
from src.handlers.session.manager import SessionHandler
from src.classifier.adapter import ClassifierToolAdapter

from .language import is_mostly_english
from ...config import TOOL_LANGUAGE_FILTER

logger = logging.getLogger(__name__)


async def _run_classifier_toolcall(
    session_id: str,
    user_utt: str,
    req_id: str,
    *,
    classifier_adapter: ClassifierToolAdapter,
    session_handler: SessionHandler,
) -> dict[str, Any]:
    """Run tool call using classifier model.

    This is much faster than the vLLM path since it uses a lightweight
    classification model instead of an autoregressive LLM.

    The classifier adapter handles history formatting and trimming
    using its own tokenizer (centralized, DRY).
    """
    t0 = time.perf_counter()

    # Snapshot trimmed user-only history (most recent last, already token-limited)
    tool_history = session_handler.get_tool_history_text(
        session_id,
        max_tokens=classifier_adapter.max_history_tokens,
    )

    def _classify_sync() -> str:
        """Run classifier inference in a worker thread."""
        return classifier_adapter.run_tool_inference(user_utt, tool_history)

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _classify_sync)

    dt_ms = (time.perf_counter() - t0) * 1000.0
    m = get_metrics()
    m.tool_classification_latency.record(dt_ms / 1000.0)
    m.tool_classifications_total.add(1)
    add_breadcrumb("Tool classified", category="tool", data={"result": text, "ms": dt_ms})
    logger.info(
        "tool_runner[classifier]: done session_id=%s req_id=%s result=%s ms=%.1f", session_id, req_id, text, dt_ms
    )

    return {"cancelled": False, "text": text}


async def run_toolcall(
    session_id: str,
    user_utt: str,
    session_handler: SessionHandler,
    classifier_adapter: ClassifierToolAdapter,
    language_detector: Any | None,
    request_id: str | None = None,
    mark_active: bool = True,
) -> dict[str, Any]:
    """Execute tool classification pipeline.

    Runs the full tool detection pipeline:
    1. Language filter for non-English
    2. Classifier model for intent detection

    Args:
        session_id: Session for history lookup and request tracking.
        user_utt: User message to classify.
        request_id: Optional request ID for tracking.
        mark_active: Whether to mark this as the active request.

    Returns:
        Dict with keys:
        - cancelled: bool (False unless interrupted)
        - text: JSON string of tool array, e.g. '[{"name": "take_screenshot"}]'
        - timeout: bool (only if timed out)
    """
    req_id = request_id or f"tool-{uuid.uuid4()}"

    # Language filter: skip tool call if message is not mostly English
    if TOOL_LANGUAGE_FILTER and not is_mostly_english(user_utt, language_detector):
        logger.info("tool_runner: skipped (non-English) session_id=%s req_id=%s", session_id, req_id)
        return {"cancelled": False, "text": "[]"}

    if mark_active:
        session_handler.set_active_request(session_id, req_id)

    # Route to classifier
    return await _run_classifier_toolcall(
        session_id,
        user_utt,
        req_id,
        classifier_adapter=classifier_adapter,
        session_handler=session_handler,
    )


def launch_tool_request(
    session_id: str,
    user_utt: str,
    *,
    session_handler: SessionHandler,
    classifier_adapter: ClassifierToolAdapter,
    language_detector: Any | None,
) -> tuple[str, asyncio.Task[dict[str, Any]]]:
    """Create a tool request task and register its request ID."""
    tool_req_id = f"tool-{uuid.uuid4()}"
    session_handler.set_tool_request(session_id, tool_req_id)
    tool_task = asyncio.create_task(
        run_toolcall(
            session_id,
            user_utt,
            session_handler=session_handler,
            classifier_adapter=classifier_adapter,
            language_detector=language_detector,
            request_id=tool_req_id,
            mark_active=False,
        )
    )
    return tool_req_id, tool_task


__all__ = ["run_toolcall", "launch_tool_request"]
