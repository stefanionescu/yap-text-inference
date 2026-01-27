"""Main runner for interactive live sessions.

This module provides the run function that orchestrates the live session:
connects to the server, handles the warm history flag, runs the interactive
loop, and manages connection lifecycle and errors.
"""

from __future__ import annotations

import uuid
import asyncio
import logging

import websockets  # type: ignore[import-not-found]

from tests.helpers.fmt import dim, section_header
from tests.helpers.websocket import with_api_key, connect_with_retries
from tests.messages.history import WARM_HISTORY, HISTORY_RECALL_MESSAGES
from tests.config import DEFAULT_WS_PING_TIMEOUT, DEFAULT_WS_PING_INTERVAL
from tests.helpers.errors import ServerError, IdleTimeoutError, ConnectionClosedError

from .client import LiveClient
from .session import LiveSession
from .personas import PersonaRegistry
from .cli import print_help, interactive_loop

logger = logging.getLogger("live")


async def run(
    server_url: str,
    api_key: str | None,
    persona_name: str,
    timeout: float,
    sampling: dict[str, float | int] | None,
    warm: bool,
    message: list[str] | None,
) -> None:
    """Run the interactive live session."""
    registry = PersonaRegistry()
    try:
        persona = registry.require(persona_name)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    # Determine initial message and history based on --warm flag
    if warm:
        initial_history = list(WARM_HISTORY)
        initial_message = HISTORY_RECALL_MESSAGES[0]
    else:
        initial_history = []
        initial_message = (
            " ".join(message).strip() if message else "Hey!"
        )

    session = LiveSession(
        session_id=f"live-{uuid.uuid4()}",
        persona=persona,
        history=initial_history,
        sampling=sampling,
    )

    # Print header and banner
    print(f"\n{section_header('LIVE SESSION')}")
    print(dim(f"  server: {server_url}"))
    print(dim(f"  persona: {persona.name} ({persona.personality}/{persona.gender})"))
    if warm:
        print(dim(f"  warm history: {len(initial_history)} messages"))
    print_help(persona.name)

    ws_url = with_api_key(server_url, api_key=api_key)
    try:
        async with connect_with_retries(
            lambda: websockets.connect(
                ws_url,
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
    except asyncio.TimeoutError:
        logger.error("Timed out while connecting to %s", server_url)
        raise SystemExit(1) from None
    except (websockets.ConnectionClosedError, websockets.ConnectionClosedOK) as exc:
        close_code = getattr(exc, "code", None)
        close_reason = getattr(exc, "reason", None)
        if close_code == 4000 or (close_reason and "idle" in str(close_reason).lower()):
            logger.info("Session ended due to inactivity. Goodbye!")
        else:
            logger.warning("Server closed the connection (code=%s). Exiting.", close_code)
    except IdleTimeoutError:
        logger.info("Session ended due to inactivity. Goodbye!")
    except ServerError as exc:
        if exc.error_code == "authentication_failed":
            logger.error(
                "Authentication failed: server rejected the provided API key. "
                "Double-check `--api-key` or `TEXT_API_KEY`."
            )
            raise SystemExit(1) from exc
        if exc.error_code == "server_at_capacity":
            logger.error("Server is busy. Please try again later.")
            raise SystemExit(1) from exc
        logger.error("Server error: %s", exc)
        raise SystemExit(1) from exc
    except ConnectionClosedError as exc:
        logger.warning("Connection closed: %s", exc)
    except Exception:
        logger.exception("Unexpected error while running live client")


__all__ = ["run"]

