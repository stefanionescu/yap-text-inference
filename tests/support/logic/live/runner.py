"""Main runner for interactive live sessions.

This module provides the run function that orchestrates the live session:
connects to the server, handles the warm history flag, runs the interactive
loop, and manages connection lifecycle and errors.
"""

from __future__ import annotations

import uuid
import logging
import websockets
from typing import Any
from .client import LiveClient
from .commands import print_help
from .cli import interactive_loop
from .personas import PersonaRegistry
from tests.config.defaults import WS_IDLE_CLOSE_CODE
from tests.state import LiveSession, StartPayloadMode
from tests.support.helpers.fmt import dim, section_header
from tests.config import DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.support.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES
from tests.support.helpers.errors import ServerError, IdleTimeoutError, ConnectionClosedError
from tests.support.helpers.websocket import ws_connect, with_api_key, connect_with_retries, build_api_key_headers

logger = logging.getLogger("live")


def _prepare_session(
    registry: PersonaRegistry,
    persona_name: str,
    warm: bool,
    message: list[str] | None,
    sampling: dict[str, float | int] | None,
    start_payload_mode: StartPayloadMode,
) -> tuple[LiveSession, Any, list[dict[str, str]], str]:
    persona = registry.require(persona_name)
    if warm:
        initial_history = list(WARM_HISTORY)
        initial_message = HISTORY_RECALL_MESSAGES[0]
    else:
        initial_history = []
        initial_message = " ".join(message).strip() if message else "Hey!"

    session = LiveSession(
        session_id=f"live-{uuid.uuid4()}",
        persona=persona,
        history=initial_history,
        sampling=sampling,
        start_payload_mode=start_payload_mode,
    )

    return session, persona, initial_history, initial_message


def _print_banner(server_url: str, persona: Any, warm: bool, initial_history: list[dict[str, str]]) -> None:
    print(f"\n{section_header('LIVE SESSION')}")
    print(dim(f"  server: {server_url}"))
    print(dim(f"  persona: {persona.name} ({persona.personality}/{persona.gender})"))
    if warm:
        print(dim(f"  warm history: {len(initial_history)} messages"))
    print_help(persona.name)


async def _run_session(
    ws_url: str,
    ws_headers: dict[str, str],
    session: LiveSession,
    timeout: float,
    registry: PersonaRegistry,
    initial_message: str,
) -> None:
    async with connect_with_retries(
        lambda: ws_connect(
            ws_url,
            headers=ws_headers,
            max_queue=None,
            ping_interval=DEFAULT_WS_PING_INTERVAL,
            ping_timeout=DEFAULT_WS_PING_TIMEOUT,
        )
    ) as ws:
        client = LiveClient(ws, session, timeout)
        try:
            await client.send_initial_message(initial_message)
            await interactive_loop(client, registry, show_banner=False)
        finally:
            await client.close()


def _log_ws_close(exc: Exception) -> None:
    close_code = getattr(exc, "code", None)
    close_reason = getattr(exc, "reason", None)
    if close_code == WS_IDLE_CLOSE_CODE or (close_reason and "idle" in str(close_reason).lower()):
        logger.info("Session ended due to inactivity. Goodbye!")
    else:
        logger.warning("Server closed the connection (code=%s). Exiting.", close_code)


def _raise_for_server_error(exc: ServerError) -> None:
    if exc.error_code == "authentication_failed":
        logger.error(
            "Authentication failed: server rejected the provided API key. Double-check `--api-key` or `TEXT_API_KEY`."
        )
        raise SystemExit(1) from exc
    if exc.error_code == "server_at_capacity":
        logger.error("Server is busy. Please try again later.")
        raise SystemExit(1) from exc
    logger.error("Server error: %s", exc)
    raise SystemExit(1) from exc


async def run(
    server_url: str,
    api_key: str | None,
    persona_name: str,
    timeout: float,
    sampling: dict[str, float | int] | None,
    warm: bool,
    message: list[str] | None,
    start_payload_mode: StartPayloadMode = "all",
) -> None:
    """Run the interactive live session."""
    registry = PersonaRegistry()
    try:
        session, persona, initial_history, initial_message = _prepare_session(
            registry,
            persona_name,
            warm,
            message,
            sampling,
            start_payload_mode,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    _print_banner(server_url, persona, warm, initial_history)

    ws_url = with_api_key(server_url, api_key=api_key)
    ws_headers = build_api_key_headers(api_key=api_key)
    try:
        await _run_session(ws_url, ws_headers, session, timeout, registry, initial_message)
    except TimeoutError:
        logger.error("Timed out while connecting to %s", server_url)
        raise SystemExit(1) from None
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
        _log_ws_close(exc)
    except IdleTimeoutError:
        logger.info("Session ended due to inactivity. Goodbye!")
    except ServerError as exc:
        _raise_for_server_error(exc)
    except ConnectionClosedError as exc:
        logger.warning("Connection closed: %s", exc)
    except Exception:
        logger.exception("Unexpected error while running live client")


__all__ = ["run"]
