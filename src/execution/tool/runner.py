"""Tool execution logic for processing tool calls.

This module runs the tool classification pipeline that determines
whether a user message requires special handling (screenshot, control commands).
"""

from __future__ import annotations

import time
import uuid
import asyncio
import logging
from typing import Any
from src.tool.adapter import ToolAdapter
from src.state.session import SessionState
from src.telemetry.sentry import add_breadcrumb
from src.telemetry.instruments import get_metrics
from src.telemetry.phases import record_phase_latency
from src.handlers.session.manager import SessionHandler

logger = logging.getLogger(__name__)


async def _run_tool_call(
    state: SessionState,
    req_id: str,
    *,
    tool_user_utt: str,
    tool_adapter: ToolAdapter,
    session_handler: SessionHandler,
) -> dict[str, Any]:
    """Run tool call using tool model."""
    t0 = time.perf_counter()

    tool_history = session_handler._history.get_tool_history_text(
        state,
        include_latest=False,
    )

    def _classify_sync() -> str:
        return tool_adapter.run_tool_inference(tool_user_utt, tool_history)

    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, _classify_sync)

    dt_ms = (time.perf_counter() - t0) * 1000.0
    m = get_metrics()
    m.tool_classification_latency.record(dt_ms / 1000.0)
    m.tool_classifications_total.add(1)
    record_phase_latency("tool", dt_ms / 1000.0)
    add_breadcrumb("Tool classified", category="tool", data={"result": text, "ms": dt_ms})
    logger.info("tool_runner: done req_id=%s result=%s ms=%.1f", req_id, text, dt_ms)

    return {"cancelled": False, "text": text}


async def run_toolcall(
    state: SessionState,
    session_handler: SessionHandler,
    tool_adapter: ToolAdapter,
    tool_user_utt: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Execute tool classification pipeline."""
    req_id = request_id or f"tool-{uuid.uuid4()}"

    return await _run_tool_call(
        state,
        req_id,
        tool_user_utt=tool_user_utt,
        tool_adapter=tool_adapter,
        session_handler=session_handler,
    )


def launch_tool_request(
    state: SessionState,
    *,
    tool_user_utt: str,
    session_handler: SessionHandler,
    tool_adapter: ToolAdapter,
) -> tuple[str, asyncio.Task[dict[str, Any]]]:
    """Create a tool request task."""
    tool_req_id = f"tool-{uuid.uuid4()}"
    tool_task = asyncio.create_task(
        run_toolcall(
            state,
            session_handler=session_handler,
            tool_adapter=tool_adapter,
            tool_user_utt=tool_user_utt,
            request_id=tool_req_id,
        )
    )
    return tool_req_id, tool_task


__all__ = ["run_toolcall", "launch_tool_request"]
