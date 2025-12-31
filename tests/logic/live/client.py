"""WebSocket client for interactive live sessions.

This module provides the LiveClient class that wraps a WebSocket connection
and provides high-level methods for sending messages, changing personas, and
streaming responses. It handles message parsing, error reporting, and stats
logging.

Error Handling:
    The client uses a two-tier error handling strategy:
    
    1. Fatal errors (thrown): Connection issues, auth failures, and other
       errors that require closing the connection. These raise exceptions.
    
    2. Recoverable errors (returned): Rate limits and transient errors that
       can be displayed to the user without closing the connection. These
       are returned as StreamResult objects with error information.
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
    error_from_close,
    is_idle_timeout_close,
)
from tests.helpers.message import iter_messages
from tests.helpers.ws import send_client_end

from .errors import LiveClientError, LiveConnectionClosed, LiveServerError
from .personas import PersonaDefinition
from .session import LiveSession
from .stream import StreamTracker, round_ms

logger = logging.getLogger("live")


@dataclass
class StreamResult:
    """Result of a streaming message exchange.
    
    Attributes:
        text: The assistant's response text (may be partial if error occurred).
        ok: True if the exchange completed successfully.
        error: The error that occurred, if any.
        cancelled: True if the response was cancelled.
    """

    text: str
    ok: bool = True
    error: ServerError | None = None
    cancelled: bool = False

    @property
    def is_rate_limited(self) -> bool:
        """Return True if this result was rate limited."""
        return isinstance(self.error, RateLimitError)

    @property
    def is_recoverable(self) -> bool:
        """Return True if the error is recoverable (can continue conversation)."""
        if self.error is None:
            return True
        return self.error.is_recoverable()

    def format_error(self) -> str:
        """Format the error for display to the user."""
        if self.error is None:
            return ""
        return self.error.format_for_user()


@dataclass
class _StreamPrinter:
    """Helper for printing streaming tokens to stdout."""

    printed_header: bool = False

    def write_chunk(self, chunk: str) -> None:
        """Write a token chunk to stdout with appropriate formatting."""
        if not chunk:
            return
        if not self.printed_header:
            print("\ncompanion >", end=" ", flush=True)
            self.printed_header = True
        print(chunk, end="", flush=True)

    def finish(self) -> None:
        """Finish the current response line."""
        if self.printed_header:
            print()
            print()


@dataclass
class _StreamState:
    """Track state during response streaming."""

    tracker: StreamTracker
    printer: _StreamPrinter = field(default_factory=_StreamPrinter)
    pending_chat_ttfb: float | None = None

    def handle_token(self, chunk: str) -> None:
        """Process an incoming token chunk."""
        metrics = self.tracker.record_token(chunk)
        self.printer.write_chunk(chunk)
        chat_ttfb = metrics.get("chat_ttfb_ms")
        if chat_ttfb is not None and self.pending_chat_ttfb is None:
            self.pending_chat_ttfb = chat_ttfb


class LiveClient:
    """High-level WebSocket client for interactive sessions."""

    def __init__(self, ws, session: LiveSession, recv_timeout: float) -> None:
        self.ws = ws
        self.session = session
        self.recv_timeout = recv_timeout
        self._closed = False
        self._stats_enabled = False

    async def send_initial_message(self, text: str) -> StreamResult:
        """Send the initial user message to start the session."""
        return await self.send_user_message(text)

    async def send_user_message(self, text: str) -> StreamResult:
        """Send a user message and return the result with assistant's response.
        
        Args:
            text: The user's message text.
            
        Returns:
            StreamResult containing the response and any error information.
            For recoverable errors (e.g., rate limits), ok=False but the
            connection remains open and the conversation can continue.
        """
        payload = self.session.build_start_payload(text)
        tracker = StreamTracker()
        await self._send_json(payload)
        result = await self._stream_response(tracker, print_user_prompt=False)
        if result.ok:
            self.session.append_exchange(text, result.text)
        return result

    @property
    def stats_logging_enabled(self) -> bool:
        """Return whether stats logging is enabled."""
        return self._stats_enabled

    def set_stats_logging(self, enabled: bool) -> bool:
        """Enable or disable stats logging."""
        self._stats_enabled = bool(enabled)
        return self._stats_enabled

    @property
    def is_connected(self) -> bool:
        """Return True if the WebSocket is still connected."""
        return not getattr(self.ws, "closed", True)

    @property
    def close_code(self) -> int | None:
        """Return the WebSocket close code if available."""
        return getattr(self.ws, "close_code", None)

    @property
    def close_reason(self) -> str | None:
        """Return the WebSocket close reason if available."""
        return getattr(self.ws, "close_reason", None)

    async def wait_closed(self) -> None:
        """Wait for the WebSocket to close."""
        await self.ws.wait_closed()

    async def change_persona(self, persona: PersonaDefinition) -> None:
        """Request a persona change mid-session."""
        try:
            payload = self.session.build_persona_payload(persona)
        except ValueError as exc:
            logger.warning("%s", exc)
            return
        logger.info(
            "Requesting persona change → name=%s gender=%s personality=%s",
            persona.name,
            persona.gender,
            persona.personality,
        )
        await self._send_json(payload)
        ack = await self._wait_for_chat_prompt_ack()
        if not ack.get("ok"):
            logger.error(
                "Persona update failed (code=%s): %s",
                ack.get("code"),
                ack.get("message", "unknown error"),
            )
            return
        code = ack.get("code")
        if code == 204:
            logger.info(
                "Persona already set to gender=%s personality=%s; no server-side change",
                ack.get("gender"),
                ack.get("personality"),
            )
            return
        logger.info(
            "Persona updated → gender=%s personality=%s (code=%s)",
            ack.get("gender"),
            ack.get("personality"),
            code,
        )
        self.session.replace_persona(persona)

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
        """Send a JSON payload over the WebSocket."""
        try:
            await self.ws.send(json.dumps(payload))
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            raise LiveConnectionClosed("WebSocket closed while sending payload") from exc

    async def _stream_response(
        self,
        tracker: StreamTracker,
        *,
        print_user_prompt: bool = True,
    ) -> StreamResult:
        """Stream and process the server response.
        
        Returns:
            StreamResult with the response text and success status.
            Recoverable errors (rate limits) are returned as failed results
            rather than raised, allowing the conversation to continue.
        """
        state = _StreamState(tracker)
        try:
            async for msg in iter_messages(self.ws, timeout=self.recv_timeout):
                msg_type = msg.get("type")
                if msg_type == "ack":
                    tracker.ack_seen = True
                    continue
                if msg_type == "toolcall":
                    self._handle_toolcall_frame(msg, tracker)
                    continue
                if msg_type == "token":
                    state.handle_token(msg.get("text", ""))
                    continue
                if msg_type == "final":
                    normalized = msg.get("normalized_text")
                    if normalized:
                        tracker.final_text = normalized
                    continue
                if msg_type == "connection_closed":
                    return self._handle_connection_closed(msg, tracker)
                if msg_type == "done":
                    return self._handle_done_frame(msg, state, print_user_prompt=print_user_prompt)
                if msg_type == "error":
                    return self._handle_error_frame(msg, state)
                logger.debug("Ignoring message type=%s payload=%s", msg_type, msg)
        except asyncio.TimeoutError as exc:
            raise LiveClientError(f"recv timeout after {self.recv_timeout:.1f}s") from exc
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            close_code = getattr(exc, "code", None)
            close_reason = getattr(exc, "reason", None)
            if is_idle_timeout_close(close_code, close_reason):
                logger.info("Server closed due to idle timeout")
                raise IdleTimeoutError(close_code=close_code, close_reason=close_reason) from exc
            logger.info("Server closed the WebSocket (code=%s)", close_code)
            asyncio.create_task(self.close())
            return StreamResult(text=tracker.final_text, ok=True)
        raise LiveClientError("WebSocket closed before receiving 'done'")

    def _handle_toolcall_frame(self, msg: dict[str, Any], tracker: StreamTracker) -> None:
        """Handle a toolcall message frame."""
        ttfb = tracker.record_toolcall()
        logger.info("TOOLCALL status=%s ttfb_ms=%s", msg.get("status"), round_ms(ttfb))

    def _handle_done_frame(
        self,
        msg: dict[str, Any],
        state: _StreamState,
        *,
        print_user_prompt: bool,
    ) -> StreamResult:
        """Handle the done message and finalize metrics."""
        state.printer.finish()
        if print_user_prompt:
            print("you >", end=" ", flush=True)
        cancelled = bool(msg.get("cancelled"))
        if state.pending_chat_ttfb is not None and self._stats_enabled:
            logger.info("CHAT ttfb_ms=%.2f", state.pending_chat_ttfb)
        if self._stats_enabled:
            logger.info(
                "metrics: %s",
                json.dumps(state.tracker.finalize_metrics(cancelled), ensure_ascii=False),
            )
        return StreamResult(
            text=state.tracker.final_text,
            ok=True,
            cancelled=cancelled,
        )

    def _handle_connection_closed(self, msg: dict[str, Any], tracker: StreamTracker) -> StreamResult:
        """Handle a connection_closed message."""
        reason = msg.get("reason") or "server_request"
        logger.info("Server signaled connection_closed reason=%s", reason)
        return StreamResult(text=tracker.final_text, ok=True)

    def _handle_error_frame(self, msg: dict[str, Any], state: _StreamState) -> StreamResult:
        """Handle an error message frame.
        
        For recoverable errors (e.g., rate limits), returns a failed StreamResult
        that the CLI can display nicely. For fatal errors, raises an exception.
        
        Args:
            msg: The error message from the server.
            state: Current stream state.
            
        Returns:
            StreamResult with error information for recoverable errors.
            
        Raises:
            LiveServerError: For fatal errors that require closing.
        """
        state.printer.finish()
        error = ServerError.from_message(msg)
        _log_server_error(msg)
        
        # Recoverable errors: return result, let CLI handle display
        if error.is_recoverable():
            return StreamResult(
                text=state.tracker.final_text,
                ok=False,
                error=error,
            )
        
        # Fatal errors: raise to close connection
        raise LiveServerError(error.message, code=error.error_code)

    async def _wait_for_chat_prompt_ack(self) -> dict[str, Any]:
        """Wait for a chat_prompt ACK message."""
        try:
            async for msg in iter_messages(self.ws, timeout=self.recv_timeout):
                msg_type = msg.get("type")
                if msg_type == "ack" and msg.get("for") == "chat_prompt":
                    return msg
                if msg_type == "error":
                    _log_server_error(msg)
                    raise LiveServerError(msg.get("message", "server error"))
        except asyncio.TimeoutError as exc:
            raise LiveClientError("timed out waiting for chat_prompt ack") from exc
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            raise LiveConnectionClosed("WebSocket closed while waiting for chat_prompt ack") from exc
        raise LiveClientError("WebSocket closed before receiving chat_prompt ack")


def _log_server_error(msg: dict[str, Any]) -> None:
    """Log a server error message."""
    logger.error(
        "Server error code=%s status=%s message=%s",
        msg.get("error_code") or msg.get("code"),
        msg.get("status"),
        msg.get("message"),
    )


__all__ = ["LiveClient", "StreamResult"]
