"""Interactive CLI entry point for the live WebSocket test client."""

from __future__ import annotations

from tests.state import InteractiveRunner

from .client import LiveClient
from .personas import PersonaRegistry


async def interactive_loop(
    client: LiveClient,
    registry: PersonaRegistry,
    *,
    show_banner: bool = True,
) -> None:
    """Run the interactive command loop."""
    runner = InteractiveRunner(client, registry, show_banner=show_banner)
    await runner.run()


__all__ = ["interactive_loop"]
