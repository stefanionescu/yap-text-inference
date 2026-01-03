"""WebSocket client for interactive live sessions.

This module provides the LiveClient class that wraps a WebSocket connection
and provides high-level methods for sending messages and streaming responses.
It handles message parsing, error reporting, and stats logging.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import websockets  # type: ignore[import-not-found]

from tests.helpers.errors import (
    ConnectionClosedError,
    IdleTimeoutError,
    RateLimitError,
    ServerError,
    TestClientError,
)
from tests.helpers.fmt import dim, cyan, magenta, format_metrics_inline
from tests.helpers.websocket import iter_messages, send_client_end
from .session import LiveSession
from .stream import (
    StreamState,
    create_tracker,
    finalize_metrics,
    record_token,
    record_toolcall,
    round_ms,
)

logger = logging.getLogger("live")


# ============================================================================
# Internal Helpers
# ============================================================================


def _log_server_error(msg: dict[str, Any]) -> None:
    """Log a server error message."""
    logger.error(
        "Server error code=%s status=%s message=%s",
        msg.get("error_code") or msg.get("code"),
        msg.get("status"),
        msg.get("message"),
    )


@dataclass
class _StreamPrinter:
    """Helper for printing streaming tokens to stdout."""

    printed_header: bool = False

    def write_chunk(self, chunk: str) -> None:
        if not chunk:
            return
        if not self.printed_header:
            print(f"\n{magenta('ASST')} ", end="", flush=True)
            self.printed_header = True
        print(chunk, end="", flush=True)

    def finish(self) -> None:
        if self.printed_header:
            print()
            print()


@dataclass
class _StreamContext:
    """Track state during response streaming."""

    state: StreamState
    printer: _StreamPrinter = field(default_factory=_StreamPrinter)
    pending_chat_ttfb: float | None = None

    def handle_token(self, chunk: str) -> None:
        metrics = record_token(self.state, chunk)
        self.printer.write_chunk(chunk)
        chat_ttfb = metrics.get("chat_ttfb_ms")
        if chat_ttfb is not None and self.pending_chat_ttfb is None:
            self.pending_chat_ttfb = chat_ttfb


# ============================================================================
# Public API
# ============================================================================


@dataclass
class StreamResult:
    """Result of a streaming message exchange."""

    text: str
    ok: bool = True
    error: ServerError | None = None
    cancelled: bool = False

    @property
    def is_rate_limited(self) -> bool:
        return isinstance(self.error, RateLimitError)

    @property
    def is_recoverable(self) -> bool:
        if self.error is None:
            return True
        return self.error.is_recoverable()

    def format_error(self) -> str:
        if self.error is None:
            return ""
        return self.error.format_for_user()


class LiveClient:
    """High-level WebSocket client for interactive sessions."""

    def __init__(self, ws, session: LiveSession, recv_timeout: float) -> None:
        self.ws = ws
        self.session = session
        self.recv_timeout = recv_timeout
        self._closed = False
        self._stats_enabled = False

    async def send_initial_message(self, text: str) -> StreamResult:
        return await self.send_user_message(text)

    async def send_user_message(self, text: str) -> StreamResult:
        """Send a user message and return the result with assistant's response."""
        payload = self.session.build_start_payload(text)
        state = create_tracker()
        await self._send_json(payload)
        result = await self._stream_response(state, print_user_prompt=False)
        if result.ok:
            self.session.append_exchange(text, result.text)
        return result

    @property
    def stats_logging_enabled(self) -> bool:
        return self._stats_enabled

    def set_stats_logging(self, enabled: bool) -> bool:
        self._stats_enabled = bool(enabled)
        return self._stats_enabled

    @property
    def is_connected(self) -> bool:
        return not getattr(self.ws, "closed", True)

    @property
    def close_code(self) -> int | None:
        return getattr(self.ws, "close_code", None)

    @property
    def close_reason(self) -> str | None:
        return getattr(self.ws, "close_reason", None)

    async def wait_closed(self) -> None:
        await self.ws.wait_closed()

    async def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._closed:
            return
        self._closed = True
        try:
            await send_client_end(self.ws)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to send client end frame: %s", exc)
        with contextlib.suppress(Exception):
            await self.ws.close(code=1000)
            await asyncio.wait_for(self.ws.wait_closed(), timeout=3.0)

    async def _send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.ws.send(json.dumps(payload))
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            raise ConnectionClosedError("WebSocket closed while sending payload") from exc

    async def _stream_response(self, state: StreamState, *, print_user_prompt: bool = True) -> StreamResult:
        """Stream and process the server response."""
        ctx = _StreamContext(state)
        try:
            async for msg in iter_messages(self.ws, timeout=self.recv_timeout):
                msg_type = msg.get("type")
                if msg_type == "ack":
                    state.ack_seen = True
                    continue
                if msg_type == "toolcall":
                    self._handle_toolcall_frame(msg, state)
                    continue
                if msg_type == "token":
                    ctx.handle_token(msg.get("text", ""))
                    continue
                if msg_type == "final":
                    if normalized := msg.get("normalized_text"):
                        state.final_text = normalized
                    continue
                if msg_type == "connection_closed":
                    return self._handle_connection_closed(msg, state)
                if msg_type == "done":
                    return self._handle_done_frame(msg, ctx, print_user_prompt=print_user_prompt)
                if msg_type == "error":
                    return self._handle_error_frame(msg, ctx)
                logger.debug("Ignoring message type=%s payload=%s", msg_type, msg)
        except asyncio.TimeoutError as exc:
            raise TestClientError(f"recv timeout after {self.recv_timeout:.1f}s") from exc
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            close_code = getattr(exc, "code", None)
            close_reason = getattr(exc, "reason", None)
            if IdleTimeoutError.matches(close_code, close_reason):
                logger.info("Server closed due to idle timeout")
                raise IdleTimeoutError(close_code=close_code, close_reason=close_reason) from exc
            logger.info("Server closed the WebSocket (code=%s)", close_code)
            asyncio.create_task(self.close())
            return StreamResult(text=state.final_text, ok=True)
        raise TestClientError("WebSocket closed before receiving 'done'")

    def _handle_toolcall_frame(self, msg: dict[str, Any], state: StreamState) -> None:
        ttfb = record_toolcall(state)
        logger.info("TOOLCALL status=%s ttfb_ms=%s", msg.get("status"), round_ms(ttfb))

    def _handle_done_frame(self, msg: dict[str, Any], ctx: _StreamContext, *, print_user_prompt: bool) -> StreamResult:
        ctx.printer.finish()
        cancelled = bool(msg.get("cancelled"))
        if self._stats_enabled:
            metrics = finalize_metrics(ctx.state, cancelled)
            print(dim(f"     {format_metrics_inline(metrics)}"))
            print()
        if print_user_prompt:
            print(f"{cyan('USER')} ", end="", flush=True)
        return StreamResult(text=ctx.state.final_text, ok=True, cancelled=cancelled)

    def _handle_connection_closed(self, msg: dict[str, Any], state: StreamState) -> StreamResult:
        reason = msg.get("reason") or "server_request"
        logger.info("Server signaled connection_closed reason=%s", reason)
        return StreamResult(text=state.final_text, ok=True)

    def _handle_error_frame(self, msg: dict[str, Any], ctx: _StreamContext) -> StreamResult:
        """Handle an error message frame."""
        ctx.printer.finish()
        error = ServerError.from_message(msg)
        _log_server_error(msg)
        if error.is_recoverable():
            return StreamResult(text=ctx.state.final_text, ok=False, error=error)
        raise error


__all__ = ["LiveClient", "StreamResult"]
