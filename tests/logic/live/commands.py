"""Command handlers for the interactive live CLI.

This module contains all slash-command handlers (/help, /list, /info, etc.)
used by the interactive loop. Each handler follows a uniform signature and
returns a boolean indicating whether the session should exit.

The command registry maps command names to handlers, with aliases for common
alternatives (e.g., /quit -> /stop, /? -> /help).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from collections.abc import Callable, Awaitable

if TYPE_CHECKING:
    from .client import LiveClient
    from .personas import PersonaRegistry

logger = logging.getLogger("live")


# ============================================================================
# Toggle Helpers
# ============================================================================

def _resolve_toggle(arg: str, current: bool) -> bool:
    """Parse a toggle argument into a boolean value."""
    if not arg:
        return not current
    normalized = arg.lower()
    if normalized in {"on", "true", "1", "enable", "enabled"}:
        return True
    if normalized in {"off", "false", "0", "disable", "disabled"}:
        return False
    raise ValueError("invalid toggle value")


def _handle_toggle_command(
    arg: str,
    *,
    getter: Callable[[], bool],
    setter: Callable[[bool], bool],
    label: str,
    command: str,
) -> None:
    """Generic toggle command handler for on/off flags."""
    try:
        new_state = _resolve_toggle(arg, getter())
    except ValueError:
        logger.warning("Usage: /%s [on|off]", command)
        return
    setter(new_state)
    logger.info("%s %s", label.capitalize(), "enabled" if new_state else "disabled")


# ============================================================================
# Command Handlers
# ============================================================================

async def _handle_help_command(
    _: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """Display the help message with available commands."""
    _ = raw_command  # unused; keeps signature uniform
    from tests.state import print_help
    print_help(client.session.persona.name, verbose=True)
    return False


async def _handle_list_command(
    _: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """List all available persona names."""
    _ = raw_command
    names = registry.available_names()
    logger.info("Available personas: %s", ", ".join(names))
    return False


async def _handle_history_command(
    _: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """Print the accumulated conversation history."""
    _ = registry, raw_command  # unused
    if client.session.history:
        print("\n--- conversation history ---")
        for msg in client.session.history:
            role = msg.get("role", "unknown").capitalize()
            content = msg.get("content", "")
            print(f"{role}: {content}")
        print("--- end history ---")
    else:
        logger.info("History is empty")
    return False


async def _handle_info_command(
    _: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """Display session and persona metadata."""
    _ = registry, raw_command
    persona = client.session.persona
    logger.info(
        "Session %s persona=%s gender=%s personality=%s history_chars=%d",
        client.session.session_id,
        persona.name,
        persona.gender,
        persona.personality,
        len(client.session.history),
    )
    return False


async def _handle_stats_command(
    arg: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """Toggle metrics and TTFB logging on/off."""
    _ = registry
    _handle_toggle_command(
        arg,
        getter=lambda: client.stats_logging_enabled,
        setter=client.set_stats_logging,
        label="stats logging (metrics + chat TTFB)",
        command=raw_command or "stats",
    )
    return False


async def _handle_stop_command(
    _: str,
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    raw_command: str,
) -> bool:
    """Stop and close the live session."""
    _ = registry, raw_command
    logger.info("Stopping live session...")
    await client.close()
    logger.info("Stopped live session.")
    return True


# ============================================================================
# Command Registry
# ============================================================================

CommandHandler = Callable[..., Awaitable[bool]]

COMMAND_HANDLERS: dict[str, CommandHandler] = {
    "help": _handle_help_command,
    "list": _handle_list_command,
    "history": _handle_history_command,
    "info": _handle_info_command,
    "stats": _handle_stats_command,
    "stop": _handle_stop_command,
}

COMMAND_ALIASES: dict[str, str] = {
    "?": "help",
    "personas": "list",
    "status": "info",
    "quit": "stop",
    "exit": "stop",
}


async def dispatch_command(
    command_line: str,
    client: LiveClient,
    registry: PersonaRegistry,
) -> bool:
    """
    Parse and dispatch a slash command.

    Returns True if the session should exit, False otherwise.
    """
    command, *rest = command_line.split(maxsplit=1)
    arg = rest[0].strip() if rest else ""
    cmd = command.lower()
    handler_key = COMMAND_ALIASES.get(cmd, cmd)
    handler = COMMAND_HANDLERS.get(handler_key)
    if handler is None:
        logger.warning("Unknown command '/%s'. Type /help for options.", command)
        return False
    return await handler(arg, client, registry, raw_command=cmd)


__all__ = ["dispatch_command"]
