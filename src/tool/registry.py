"""Central registry for configured tool runtime dependency.

Tool adapter construction is performed eagerly during server startup, then
registered here for modules that need shared access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter import ToolAdapter

_STATE: dict[str, ToolAdapter | None] = {"adapter": None}


def configure_tool_adapter(adapter: ToolAdapter | None) -> None:
    """Register the process runtime tool adapter."""
    _STATE["adapter"] = adapter


def get_tool_adapter() -> ToolAdapter:
    """Return the configured tool adapter."""
    adapter = _STATE["adapter"]
    if adapter is None:
        raise RuntimeError("Tool adapter has not been configured in runtime bootstrap")
    return adapter


def reset_tool_adapter() -> None:
    """Clear configured tool adapter (for tests/shutdown)."""
    configure_tool_adapter(None)


__all__ = [
    "configure_tool_adapter",
    "get_tool_adapter",
    "reset_tool_adapter",
]
