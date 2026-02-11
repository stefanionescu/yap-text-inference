"""Central registry for configured classifier runtime dependency.

Classifier construction is performed eagerly during server startup, then
registered here for modules that need shared access.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .adapter import ClassifierToolAdapter

_STATE: dict[str, ClassifierToolAdapter | None] = {"adapter": None}


def configure_classifier_adapter(adapter: ClassifierToolAdapter | None) -> None:
    """Register the process runtime classifier adapter."""
    _STATE["adapter"] = adapter


def get_classifier_adapter() -> ClassifierToolAdapter:
    """Return the configured classifier adapter."""
    adapter = _STATE["adapter"]
    if adapter is None:
        raise RuntimeError("Classifier adapter has not been configured in runtime bootstrap")
    return adapter


def reset_classifier_adapter() -> None:
    """Clear configured classifier adapter (for tests/shutdown)."""
    configure_classifier_adapter(None)


__all__ = [
    "configure_classifier_adapter",
    "get_classifier_adapter",
    "reset_classifier_adapter",
]
