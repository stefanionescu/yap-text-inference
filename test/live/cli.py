from __future__ import annotations

import asyncio
import logging

from .client import LiveClient
from .errors import LiveClientError, LiveInputClosed
from .personas import PersonaRegistry

logger = logging.getLogger("live")


async def interactive_loop(client: LiveClient, registry: PersonaRegistry) -> None:
    _print_help(registry.available_names(), client.session.persona.name)
    while True:
        try:
            line = (await _ainput("live> ")).strip()
        except LiveInputClosed:
            logger.info("stdin closed; ending session")
            break
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            break

        if not line:
            continue
        if line.startswith("/"):
            should_exit = await _handle_command(line[1:], client, registry)
            if should_exit:
                break
            continue

        try:
            await client.send_user_message(line)
        except LiveClientError as exc:
            logger.error("send failed: %s", exc)
            raise


async def _handle_command(command_line: str, client: LiveClient, registry: PersonaRegistry) -> bool:
    command, *rest = command_line.split(maxsplit=1)
    arg = rest[0].strip() if rest else ""
    cmd = command.lower()

    if cmd in {"quit", "exit", "stop"}:
        logger.info("Stopping live session on user request")
        return True
    if cmd in {"help", "?"}:
        _print_help(registry.available_names(), client.session.persona.name, verbose=True)
        return False
    if cmd in {"list", "personas"}:
        names = registry.available_names()
        logger.info("Available personas: %s", ", ".join(names))
        return False
    if cmd in {"persona", "personality"}:
        if not arg:
            logger.warning("Usage: /persona <name>")
            return False
        try:
            persona = registry.require(arg)
        except ValueError as exc:
            logger.error("%s", exc)
            return False
        try:
            await client.change_persona(persona)
        except LiveClientError as exc:
            logger.error("persona update failed: %s", exc)
        return False
    if cmd == "history":
        if client.session.history:
            print("\n--- conversation history ---")
            print(client.session.history)
            print("--- end history ---")
        else:
            logger.info("History is empty")
        return False
    if cmd in {"info", "status"}:
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

    logger.warning("Unknown command '/%s'. Type /help for options.", command)
    return False


async def _ainput(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except EOFError as exc:
        raise LiveInputClosed("stdin closed") from exc


def _print_help(names: list[str], current: str, verbose: bool = False) -> None:
    available = ", ".join(names) if names else "<none>"
    if verbose:
        print(
            "\nCommands:\n"
            "  /help                Show this message\n"
            "  /list                Show persona names (hot-reloaded)\n"
            "  /persona <name>      Switch persona+gender mid-session\n"
            "  /history             Print accumulated conversation log\n"
            "  /info                Show session/persona metadata\n"
            "  /stop|/quit          Stop and close the session\n"
            "\n"
            "Any line without a leading '/' is sent to the assistant.\n"
            "Personas are loaded from test/prompts/live.py (default: anna_flirty).\n"
        )
    else:
        print(
            "\nInteractive mode ready. Type /help for commands.\n"
            f"Current persona: {current} | Available: {available}\n"
        )


__all__ = ["interactive_loop"]


