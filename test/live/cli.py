from __future__ import annotations

import asyncio
import contextlib
import logging
import signal
from dataclasses import dataclass
from typing import Callable

from .client import LiveClient
from .errors import LiveClientError, LiveConnectionClosed, LiveInputClosed
from .personas import PersonaRegistry

logger = logging.getLogger("live")


@dataclass(slots=True)
class InteractiveRunner:
    client: LiveClient
    registry: PersonaRegistry
    stdin_task: asyncio.Task[str] | None = None
    _closing: bool = False

    async def run(self) -> None:
        loop = asyncio.get_running_loop()
        sigint_installed = False
        disconnect_task: asyncio.Task | None = None
        try:
            loop.add_signal_handler(signal.SIGINT, self._handle_sigint)
            sigint_installed = True
        except (NotImplementedError, RuntimeError):
            logger.warning("Signal handlers unavailable; Ctrl+C may be noisy")
        try:
            disconnect_task = asyncio.create_task(self._watch_disconnect())
            await self._loop()
        finally:
            if disconnect_task:
                disconnect_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await disconnect_task
            if sigint_installed:
                loop.remove_signal_handler(signal.SIGINT)

    async def _loop(self) -> None:
        self._print_banner()
        while True:
            try:
                line = await self._read_line()
            except LiveInputClosed as exc:
                logger.info("%s", exc)
                break
            except LiveClientError as exc:
                logger.error("send failed: %s", exc)
                raise

            if not line:
                continue
            if line.startswith("/"):
                should_exit = await _handle_command(line[1:], self.client, self.registry)
                if should_exit:
                    break
                continue

            try:
                await self.client.send_user_message(line)
            except LiveConnectionClosed:
                logger.warning("Connection closed; exiting interactive mode.")
                break

    async def _read_line(self) -> str:
        loop = asyncio.get_running_loop()
        if self.stdin_task:
            self.stdin_task.cancel()
        self.stdin_task = loop.create_task(_ainput("you > "))
        try:
            line = await self.stdin_task
        except asyncio.CancelledError as exc:
            raise LiveInputClosed("input cancelled") from exc
        finally:
            self.stdin_task = None
        return line.strip()

    def _handle_sigint(self) -> None:
        if self._closing:
            return
        self._closing = True
        logger.info("Ctrl+C received; closing session...")
        if self.stdin_task:
            self.stdin_task.cancel()
        asyncio.create_task(self.client.close())

    def _print_banner(self) -> None:
        _print_help(self.registry.available_names(), self.client.session.persona.name)

    async def _watch_disconnect(self) -> None:
        try:
            await self.client.wait_closed()
        except asyncio.CancelledError:
            return
        if self._closing:
            return
        self._closing = True
        logger.warning(
            "Server closed the connection (code=%s reason=%s); exiting.",
            self.client.close_code,
            self.client.close_reason,
        )
        if self.stdin_task:
            self.stdin_task.cancel()


async def interactive_loop(client: LiveClient, registry: PersonaRegistry) -> None:
    runner = InteractiveRunner(client, registry)
    await runner.run()


async def _handle_command(command_line: str, client: LiveClient, registry: PersonaRegistry) -> bool:
    command, *rest = command_line.split(maxsplit=1)
    arg = rest[0].strip() if rest else ""
    cmd = command.lower()

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
    if cmd in {"stats"}:
        _handle_toggle_command(
            arg,
            getter=lambda: client.stats_logging_enabled,
            setter=client.set_stats_logging,
            label="stats logging (metrics + chat TTFB)",
            command="stats",
        )
        return False
    if cmd in {"stop", "quit", "exit"}:
        logger.info("Stopping live session...")
        await client.close()
        logger.info("Stopped live session.")
        return True

    logger.warning("Unknown command '/%s'. Type /help for options.", command)
    return False


async def _ainput(prompt: str) -> str:
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except EOFError as exc:
        raise LiveInputClosed("stdin closed") from exc
    except KeyboardInterrupt as exc:
        raise LiveInputClosed("keyboard interrupt") from exc


def _print_help(names: list[str], current: str, verbose: bool = False) -> None:
    if verbose:
        print(
            "\nCommands:\n"
            "  /help                Show this message\n"
            "  /list                Show persona names\n"
            "  /persona <name>      Switch persona+gender mid-session\n"
            "  /history             Print accumulated conversation log\n"
            "  /info                Show session/persona metadata\n"
            "  /stats [on|off]      Toggle metrics + chat TTFB logging\n"
            "  /stop|/quit          Stop and close the session\n"
            "\n"
            "Any line without a leading '/' is sent to the assistant.\n"
            "Personas are loaded from test/prompts/live.py (default: anna_flirty).\n"
        )
    else:
        print(
            "\nInteractive mode ready. Type /help for commands.\n"
            f"Current persona: {current}\n"
        )


def _handle_toggle_command(
    arg: str,
    *,
    getter: Callable[[], bool],
    setter: Callable[[bool], bool],
    label: str,
    command: str,
) -> None:
    try:
        new_state = _resolve_toggle(arg, getter())
    except ValueError:
        logger.warning("Usage: /%s [on|off]", command)
        return
    setter(new_state)
    logger.info("%s %s", label.capitalize(), "enabled" if new_state else "disabled")


def _resolve_toggle(arg: str, current: bool) -> bool:
    if not arg:
        return not current
    normalized = arg.lower()
    if normalized in {"on", "true", "1", "enable", "enabled"}:
        return True
    if normalized in {"off", "false", "0", "disable", "disabled"}:
        return False
    raise ValueError("invalid toggle value")


__all__ = ["interactive_loop"]


