from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

import websockets  # type: ignore[import-not-found]

from test.common.message import iter_messages
from test.common.ws import send_client_end

from .errors import LiveClientError, LiveConnectionClosed, LiveServerError
from .personas import PersonaDefinition
from .session import LiveSession
from .stream import StreamTracker, round_ms

logger = logging.getLogger("live")


class LiveClient:
    def __init__(self, ws, session: LiveSession, recv_timeout: float) -> None:
        self.ws = ws
        self.session = session
        self.recv_timeout = recv_timeout
        self._closed = False
        self._stats_enabled = False

    async def send_initial_message(self, text: str) -> str:
        return await self.send_user_message(text)

    async def send_user_message(self, text: str) -> str:
        payload = self.session.build_start_payload(text)
        tracker = StreamTracker()
        await self._send_json(payload)
        response = await self._stream_response(tracker, print_user_prompt=False)
        self.session.append_exchange(text, response)
        return response

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

    async def change_persona(self, persona: PersonaDefinition) -> None:
        payload = self.session.build_persona_payload(persona)
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
        if self._closed:
            return
        self._closed = True
        try:
            await send_client_end(self.ws)
        except asyncio.CancelledError:
            # Preserve cancellation but still attempt to close the socket.
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
            raise LiveConnectionClosed("WebSocket closed while sending payload") from exc

    async def _stream_response(
        self,
        tracker: StreamTracker,
        *,
        print_user_prompt: bool = True,
    ) -> str:
        printed_header = False
        pending_chat_ttfb: float | None = None
        try:
            async for msg in iter_messages(self.ws, timeout=self.recv_timeout):
                msg_type = msg.get("type")
                if msg_type == "ack":
                    tracker.ack_seen = True
                    continue
                if msg_type == "toolcall":
                    ttfb = tracker.record_toolcall()
                    logger.info("TOOLCALL status=%s ttfb_ms=%s", msg.get("status"), round_ms(ttfb))
                    continue
                if msg_type == "token":
                    chunk = msg.get("text", "")
                    metrics = tracker.record_token(chunk)
                    if not printed_header:
                        print("\ncompanion >", end=" ", flush=True)
                        printed_header = True
                    print(chunk, end="", flush=True)
                    chat_ttfb = metrics.get("chat_ttfb_ms")
                    if chat_ttfb is not None and pending_chat_ttfb is None:
                        pending_chat_ttfb = chat_ttfb
                    continue
                if msg_type == "final":
                    normalized = msg.get("normalized_text")
                    if normalized:
                        tracker.final_text = normalized
                    continue
                if msg_type == "connection_closed":
                    reason = msg.get("reason") or "server_request"
                    logger.info("Server signaled connection_closed reason=%s", reason)
                    return tracker.final_text
                if msg_type == "done":
                    if printed_header:
                        print()
                        print()
                    if print_user_prompt:
                        print("you >", end=" ", flush=True)
                    cancelled = bool(msg.get("cancelled"))
                    if pending_chat_ttfb is not None and self._stats_enabled:
                        logger.info("CHAT ttfb_ms=%.2f", pending_chat_ttfb)
                    if self._stats_enabled:
                        logger.info(
                            "metrics: %s",
                            json.dumps(tracker.finalize_metrics(cancelled), ensure_ascii=False),
                        )
                    return tracker.final_text
                if msg_type == "error":
                    _log_server_error(msg)
                    raise LiveServerError(msg.get("message", "server error"), code=msg.get("error_code"))
                logger.debug("Ignoring message type=%s payload=%s", msg_type, msg)
        except asyncio.TimeoutError as exc:
            raise LiveClientError(f"recv timeout after {self.recv_timeout:.1f}s") from exc
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK):
            logger.info("Server closed the WebSocket")
            asyncio.create_task(self.close())
            return tracker.final_text
        raise LiveClientError("WebSocket closed before receiving 'done'")

    async def _wait_for_chat_prompt_ack(self) -> dict[str, Any]:
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
    logger.error(
        "Server error code=%s status=%s message=%s",
        msg.get("error_code") or msg.get("code"),
        msg.get("status"),
        msg.get("message"),
    )


__all__ = ["LiveClient"]


