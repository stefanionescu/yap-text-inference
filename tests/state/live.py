"""Live client dataclasses and helpers."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import signal
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from tests.helpers.errors import (
    ConnectionClosedError,
    IdleTimeoutError,
    InputClosedError,
    RateLimitError,
    ServerError,
    TestClientError,
)
from tests.helpers.fmt import bold, cyan, dim, magenta, yellow
from tests.helpers.websocket import build_start_payload as build_ws_start_payload
from tests.helpers.websocket import record_token
from tests.logic.live.commands import dispatch_command

from .metrics import SessionContext, StreamState

if TYPE_CHECKING:
    from tests.logic.live.client import LiveClient
    from tests.logic.live.personas import PersonaRegistry

logger = logging.getLogger("live")


@dataclass(frozen=True)
class PersonaDefinition:
    """Immutable representation of a persona configuration."""

    name: str
    gender: str
    personality: str
    prompt: str


@dataclass
class LiveSession:
    """Live test session state."""

    session_id: str
    persona: PersonaDefinition
    history: list[dict[str, str]] = field(default_factory=list)
    sampling: dict[str, float | int] | None = None

    def build_start_payload(self, user_text: str) -> dict[str, object]:
        """Build the start message payload for a conversation turn."""
        ctx = SessionContext(
            session_id=self.session_id,
            gender=self.persona.gender,
            personality=self.persona.personality,
            chat_prompt=self.persona.prompt,
            sampling=self.sampling,
        )
        return build_ws_start_payload(ctx, user_text, history=self.history)

    def append_exchange(self, user_text: str, assistant_text: str) -> None:
        self.history.append({"role": "user", "content": user_text})
        self.history.append({"role": "assistant", "content": assistant_text})


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


@dataclass(slots=True)
class InteractiveRunner:
    """Manages the interactive CLI session lifecycle."""

    client: LiveClient
    registry: PersonaRegistry
    show_banner: bool = True
    stdin_task: asyncio.Task[str] | None = None
    _closing: bool = False

    async def run(self) -> None:
        """Execute the interactive loop until exit or disconnect."""
        loop = asyncio.get_running_loop()
        sigint_installed = self._install_sigint_handler(loop)
        loop_task: asyncio.Task | None = None
        disconnect_task: asyncio.Task | None = None
        try:
            loop_task, disconnect_task = self._start_background_tasks()
            await self._coordinate_tasks(loop_task, disconnect_task)
        finally:
            await self._finalize_task(loop_task)
            await self._finalize_task(disconnect_task)
            if sigint_installed:
                loop.remove_signal_handler(signal.SIGINT)

    def _install_sigint_handler(self, loop: asyncio.AbstractEventLoop) -> bool:
        """Install a signal handler for graceful Ctrl+C handling."""
        try:
            loop.add_signal_handler(signal.SIGINT, self._handle_sigint)
            return True
        except (NotImplementedError, RuntimeError):
            logger.warning("Signal handlers unavailable; Ctrl+C may be noisy")
            return False

    def _start_background_tasks(self) -> tuple[asyncio.Task, asyncio.Task]:
        """Create background tasks for input loop and disconnect monitoring."""
        loop_task = asyncio.create_task(self._loop())
        disconnect_task = asyncio.create_task(self._watch_disconnect())
        return loop_task, disconnect_task

    async def _coordinate_tasks(
        self,
        loop_task: asyncio.Task,
        disconnect_task: asyncio.Task,
    ) -> None:
        """Wait for either input loop or disconnect, then clean up the other."""
        done, _ = await asyncio.wait(
            {loop_task, disconnect_task},
            return_when=asyncio.FIRST_COMPLETED,
        )
        if disconnect_task in done:
            await self._cancel_task(
                loop_task,
                suppress=(asyncio.CancelledError, InputClosedError, ConnectionClosedError),
            )
        else:
            await self._cancel_task(disconnect_task)

    async def _cancel_task(
        self,
        task: asyncio.Task,
        *,
        suppress: tuple[type[BaseException], ...] = (asyncio.CancelledError,),
    ) -> None:
        """Cancel a task and suppress specified exceptions."""
        if task.done():
            return
        task.cancel()
        with contextlib.suppress(*suppress):
            await task

    async def _finalize_task(self, task: asyncio.Task | None) -> None:
        """Ensure a task is cancelled and awaited during cleanup."""
        if not task:
            return
        if not task.done():
            await self._cancel_task(task)
        else:
            with contextlib.suppress(asyncio.CancelledError):
                await task

    async def _loop(self) -> None:
        """Main input loop: read lines and dispatch commands or messages."""
        if self.show_banner:
            print_help(self.client.session.persona.name)
        while True:
            try:
                line = await self._read_line()
            except InputClosedError as exc:
                if not self._closing:
                    logger.info("%s", exc)
                else:
                    logger.debug("stdin closed while shutting down: %s", exc)
                break
            except TestClientError as exc:
                logger.error("send failed: %s", exc)
                raise

            if not line:
                continue
            if line.startswith("/"):
                should_exit = await dispatch_command(line[1:], self.client, self.registry)
                if should_exit:
                    break
                continue

            try:
                result = await self.client.send_user_message(line)
                if not result.ok:
                    self._print_error(result.format_error())
                    if not result.is_recoverable:
                        logger.warning("Fatal error; exiting interactive mode.")
                        break
            except ConnectionClosedError:
                logger.warning("Connection closed; exiting interactive mode.")
                break
            except IdleTimeoutError:
                logger.warning("Connection closed due to inactivity; exiting.")
                break

    async def _read_line(self) -> str:
        """Read a line from stdin asynchronously."""
        loop = asyncio.get_running_loop()
        if self.stdin_task:
            self.stdin_task.cancel()
        self.stdin_task = loop.create_task(_ainput(f"{cyan('USER')} "))
        try:
            line = await self.stdin_task
        except asyncio.CancelledError as exc:
            raise InputClosedError("input cancelled") from exc
        finally:
            self.stdin_task = None
        return line.strip()

    def _handle_sigint(self) -> None:
        """Handle Ctrl+C by initiating graceful shutdown."""
        if self._closing:
            return
        self._closing = True
        logger.info("Ctrl+C received; closing session...")
        if self.stdin_task:
            self.stdin_task.cancel()
        asyncio.create_task(self.client.close())

    def _print_error(self, message: str) -> None:
        """Print an error message in a user-friendly format."""
        print(f"\n{yellow('WARN')}  {message}\n")
        print(f"{cyan('USER')} ", end="", flush=True)

    async def _watch_disconnect(self) -> None:
        """Monitor for server disconnect and trigger shutdown if needed."""
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
        os._exit(0)


async def _ainput(prompt: str) -> str:
    """Async wrapper around input() that runs in an executor."""
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(None, lambda: input(prompt))
    except EOFError as exc:
        raise InputClosedError("stdin closed") from exc
    except KeyboardInterrupt as exc:
        raise InputClosedError("keyboard interrupt") from exc


def print_help(current: str, verbose: bool = False) -> None:
    """Print the help banner or detailed command list."""
    if verbose:
        print(
            f"\n{bold('Commands:')}\n"
            f"  {dim('/help')}                Get help with a command\n"
            f"  {dim('/list')}                Show persona names\n"
            f"  {dim('/history')}             Print accumulated conversation log\n"
            f"  {dim('/info')}                Show session/persona metadata\n"
            f"  {dim('/stats [on|off]')}      Toggle metrics logging\n"
            f"  {dim('/stop|/quit')}          Stop and close the session\n"
            "\n"
            "Any line without a leading '/' is sent to the assistant.\n"
            "Use /list to see available personas.\n"
        )
    else:
        print(
            f"\n{bold('Interactive mode ready.')} Type /help for commands.\n"
            f"Current persona: {current}\n"
        )


__all__ = [
    "InteractiveRunner",
    "LiveSession",
    "PersonaDefinition",
    "StreamResult",
    "_StreamContext",
    "_StreamPrinter",
    "print_help",
]
