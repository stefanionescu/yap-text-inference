"""Concurrent execution: tool and chat models run in parallel."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass
from typing import Awaitable

from fastapi import WebSocket

from .tool_parser import parse_tool_result
from .chat_streamer import run_chat_stream
from ..engines import get_chat_engine
from ..handlers.session_handler import session_handler
from ..config.timeouts import TOOL_HARD_TIMEOUT_MS, PREBUFFER_MAX_CHARS
from ..config import CHECK_SCREEN_PREFIX
from .executor_utils import (
    abort_tool_request,
    cancel_task,
    flush_and_send,
    launch_tool_request,
    send_toolcall,
    stream_chat_response,
)

logger = logging.getLogger(__name__)


@dataclass
class ToolDecision:
    raw_field: object
    is_tool: bool
    payload: dict | None


class ConcurrentCoordinator:
    """Coordinates concurrent tool routing and chat pre-buffering."""

    def __init__(
        self,
        *,
        ws: WebSocket,
        session_id: str,
        static_prefix: str,
        runtime_text: str,
        history_text: str,
        user_utt: str,
        chat_req_id: str,
        chat_stream,
        tool_coro: Awaitable[dict],
        tool_timeout_s: float,
        prebuffer_max_chars: int,
    ):
        self.ws = ws
        self.session_id = session_id
        self.static_prefix = static_prefix
        self.runtime_text = runtime_text
        self.history_text = history_text
        self.user_utt = user_utt
        self.chat_req_id = chat_req_id
        self.chat_stream = chat_stream
        self.tool_coro = tool_coro
        self.tool_timeout_s = tool_timeout_s
        self.prebuffer_limit = max(prebuffer_max_chars, 0)

        self._chat_iter = chat_stream.__aiter__()
        self._pending_chunk_task: asyncio.Task | None = None
        self._chat_finished = False
        self._buffer = ""
        self._tool_task = asyncio.create_task(self._collect_tool_result())

    async def run(self) -> None:
        try:
            decision = await self._await_tool_decision()
            session_handler.clear_tool_request_id(self.session_id)
            if decision.is_tool:
                await self._handle_tool_yes(decision.raw_field)
            else:
                await self._handle_tool_no(decision.raw_field)
        finally:
            await self._shutdown_pending_chunk()

    async def _await_tool_decision(self) -> ToolDecision:
        while True:
            self._ensure_chunk_task()
            wait_set = {self._tool_task}
            if self._pending_chunk_task:
                wait_set.add(self._pending_chunk_task)

            done, _ = await asyncio.wait(wait_set, return_when=asyncio.FIRST_COMPLETED)

            if self._pending_chunk_task and self._pending_chunk_task in done:
                chunk = await self._consume_pending_chunk()
                if chunk:
                    await self._maybe_flush_prebuffer(chunk)
                if self._chat_finished and self._tool_task.done():
                    break
                if not self._tool_task.done():
                    continue

            if self._tool_task in done:
                break

        tool_result = await self._tool_task
        raw_field, is_tool = parse_tool_result(tool_result)
        text_len = len((tool_result or {}).get("text") or "")
        logger.info(
            "concurrent_exec: tool decision session_id=%s is_tool=%s text_len=%s",
            self.session_id,
            is_tool,
            text_len,
        )
        return ToolDecision(raw_field=raw_field, is_tool=is_tool, payload=tool_result)

    async def _collect_tool_result(self) -> dict | None:
        try:
            if self.tool_timeout_s < 0:
                return await self.tool_coro
            return await asyncio.wait_for(self.tool_coro, timeout=self.tool_timeout_s)
        except asyncio.TimeoutError:
            await abort_tool_request(self.session_id)
            logger.info("concurrent_exec: tool timeout session_id=%s", self.session_id)
            return {"cancelled": True}

    def _ensure_chunk_task(self) -> None:
        if self._chat_finished or (self._pending_chunk_task and not self._pending_chunk_task.done()):
            return
        self._pending_chunk_task = asyncio.create_task(self._chat_iter.__anext__())

    async def _consume_pending_chunk(self) -> str | None:
        if not self._pending_chunk_task:
            return None
        task = self._pending_chunk_task
        self._pending_chunk_task = None
        try:
            return await task
        except StopAsyncIteration:
            self._chat_finished = True
            return None
        except asyncio.CancelledError:
            return None

    async def _maybe_flush_prebuffer(self, chunk: str) -> None:
        self._buffer += chunk
        if self.prebuffer_limit <= 0:
            await flush_and_send(self.ws, self._buffer)
            logger.info(
                "concurrent_exec: flushed prebuffer session_id=%s len=%s",
                self.session_id,
                len(self._buffer),
            )
            self._buffer = ""
            return
        if len(self._buffer) < self.prebuffer_limit:
            return
        await flush_and_send(self.ws, self._buffer)
        logger.info(
            "concurrent_exec: flushed prebuffer session_id=%s len=%s",
            self.session_id,
            len(self._buffer),
        )
        self._buffer = ""

    async def _handle_tool_yes(self, raw_field: object) -> None:
        await send_toolcall(self.ws, "yes", raw_field)
        logger.info("concurrent_exec: sent toolcall yes")
        await self._shutdown_pending_chunk()
        with contextlib.suppress(Exception):
            await (await get_chat_engine()).abort_request(self.chat_req_id)

        new_chat_req_id = f"chat-{uuid.uuid4()}"
        session_handler.set_active_request(self.session_id, new_chat_req_id)
        modified_user_utt = f"{CHECK_SCREEN_PREFIX} {self.user_utt}".strip()

        new_chat_stream = run_chat_stream(
            self.session_id,
            self.static_prefix,
            self.runtime_text,
            self.history_text,
            modified_user_utt,
            request_id=new_chat_req_id,
        )
        final_text = await stream_chat_response(
            self.ws,
            new_chat_stream,
            self.session_id,
            modified_user_utt,
        )
        logger.info(
            "concurrent_exec: done after tool yes session_id=%s chars=%s",
            self.session_id,
            len(final_text),
        )

    async def _handle_tool_no(self, raw_field: object) -> None:
        await send_toolcall(self.ws, "no", raw_field)
        logger.info("concurrent_exec: sent toolcall no")

        buffered = self._buffer
        if buffered:
            await flush_and_send(self.ws, buffered)
            logger.info(
                "concurrent_exec: flushed buffered chat session_id=%s len=%s",
                self.session_id,
                len(buffered),
            )
            self._buffer = ""

        first_chunk = await self._drain_pending_chunk()

        async def _remaining_stream():
            if first_chunk:
                yield first_chunk
            async for chunk in self._chat_iter:
                yield chunk

        final_text = await stream_chat_response(
            self.ws,
            _remaining_stream(),
            self.session_id,
            self.user_utt,
            initial_text=buffered,
            initial_text_already_sent=bool(buffered),
        )
        logger.info("concurrent_exec: done after tool no session_id=%s chars=%s", self.session_id, len(final_text))

    async def _drain_pending_chunk(self) -> str | None:
        if not self._pending_chunk_task:
            return None
        try:
            return await self._pending_chunk_task
        except (asyncio.CancelledError, StopAsyncIteration):
            return None
        finally:
            self._pending_chunk_task = None

    async def _shutdown_pending_chunk(self) -> None:
        if not self._pending_chunk_task:
            return
        await cancel_task(self._pending_chunk_task)
        self._pending_chunk_task = None


async def run_concurrent_execution(
    ws: WebSocket,
    session_id: str,
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
) -> None:
    """Execute concurrent tool and chat workflow with buffering."""
    tool_hard_timeout_ms = float(TOOL_HARD_TIMEOUT_MS)
    prebuffer_max_chars = int(PREBUFFER_MAX_CHARS)
    tool_timeout_s = tool_hard_timeout_ms / 1000.0 if tool_hard_timeout_ms >= 0 else -1.0
    logger.info(
        "concurrent_exec: session_id=%s tool_timeout_ms=%s prebuffer=%s",
        session_id,
        tool_hard_timeout_ms,
        prebuffer_max_chars,
    )

    chat_req_id = f"chat-{uuid.uuid4()}"
    session_handler.set_active_request(session_id, chat_req_id)

    tool_req_id, tool_coro = launch_tool_request(session_id, user_utt, history_text)
    logger.info("concurrent_exec: tool start req_id=%s", tool_req_id)

    chat_stream = run_chat_stream(
        session_id,
        static_prefix,
        runtime_text,
        history_text,
        user_utt,
        request_id=chat_req_id,
    )
    logger.info("concurrent_exec: chat start req_id=%s", chat_req_id)

    coordinator = ConcurrentCoordinator(
        ws=ws,
        session_id=session_id,
        static_prefix=static_prefix,
        runtime_text=runtime_text,
        history_text=history_text,
        user_utt=user_utt,
        chat_req_id=chat_req_id,
        chat_stream=chat_stream,
        tool_coro=tool_coro,
        tool_timeout_s=tool_timeout_s,
        prebuffer_max_chars=prebuffer_max_chars,
    )

    try:
        await coordinator.run()
    except Exception:
        with contextlib.suppress(Exception):
            await (await get_chat_engine()).abort_request(chat_req_id)
        await abort_tool_request(session_id)
        logger.exception("concurrent_exec: error")
        raise
