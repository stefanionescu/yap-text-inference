from __future__ import annotations

import asyncio
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

    async def send_initial_message(self, text: str) -> str:
        logger.info("Opening session %s with persona '%s'", self.session.session_id, self.session.persona.name)
        return await self.send_user_message(text)

    async def send_user_message(self, text: str) -> str:
        payload = self.session.build_start_payload(text)
        tracker = StreamTracker()
        logger.info("User → %s", text)
        await self._send_json(payload)
        response = await self._stream_response(tracker)
        self.session.append_exchange(text, response)
        logger.info("Assistant ← %s", response)
        return response

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
        logger.info("Sending end-of-session signal to server")
        await send_client_end(self.ws)

    async def _send_json(self, payload: dict[str, Any]) -> None:
        try:
            await self.ws.send(json.dumps(payload))
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            raise LiveConnectionClosed("WebSocket closed while sending payload") from exc

    async def _stream_response(self, tracker: StreamTracker) -> str:
        printed_header = False
        try:
            async for msg in iter_messages(self.ws, timeout=self.recv_timeout):
                msg_type = msg.get("type")
                if msg_type == "ack":
                    tracker.ack_seen = True
                    logger.info(
                        "ACK(%s) gender=%s personality=%s code=%s",
                        msg.get("for"),
                        msg.get("gender"),
                        msg.get("personality"),
                        msg.get("code"),
                    )
                    continue
                if msg_type == "toolcall":
                    ttfb = tracker.record_toolcall()
                    logger.info("TOOLCALL status=%s ttfb_ms=%s", msg.get("status"), round_ms(ttfb))
                    continue
                if msg_type == "token":
                    chunk = msg.get("text", "")
                    metrics = tracker.record_token(chunk)
                    if not printed_header:
                        print("\nassistant >", end=" ", flush=True)
                        printed_header = True
                    print(chunk, end="", flush=True)
                    chat_ttfb = metrics.get("chat_ttfb_ms")
                    if chat_ttfb is not None:
                        logger.info("CHAT ttfb_ms=%.2f", chat_ttfb)
                    continue
                if msg_type == "final":
                    normalized = msg.get("normalized_text")
                    if normalized:
                        tracker.final_text = normalized
                    continue
                if msg_type == "done":
                    if printed_header:
                        print()
                    cancelled = bool(msg.get("cancelled"))
                    logger.info("metrics: %s", json.dumps(tracker.finalize_metrics(cancelled), ensure_ascii=False))
                    return tracker.final_text
                if msg_type == "error":
                    _log_server_error(msg)
                    raise LiveServerError(msg.get("message", "server error"))
                logger.debug("Ignoring message type=%s payload=%s", msg_type, msg)
        except asyncio.TimeoutError as exc:
            raise LiveClientError(f"recv timeout after {self.recv_timeout:.1f}s") from exc
        except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
            raise LiveConnectionClosed("WebSocket closed while streaming response") from exc
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


