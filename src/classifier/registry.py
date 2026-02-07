"""Central registry for classifier singleton instance.

This module owns the classifier singleton instance, providing a single location
for lifecycle management. Entry-point code accesses the classifier through this
registry.

The registry uses lazy initialization with thread-safe locking - the classifier
is created on first access, not at import time.

Usage:
    from src.classifier.registry import get_classifier_adapter

    adapter = get_classifier_adapter()
    result = await adapter.classify(text)
"""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from .factory import create_classifier_adapter

if TYPE_CHECKING:
    from .adapter import ClassifierToolAdapter

# Singleton instance - created lazily on first access
_STATE: dict[str, ClassifierToolAdapter | None] = {"instance": None}
_lock = threading.Lock()


def get_classifier_adapter() -> ClassifierToolAdapter:
    """Get the global classifier adapter singleton.

    Lazily initializes the classifier using config values from environment
    on first access. Subsequent calls return the same instance.

    Thread Safety:
        Uses double-checked locking pattern to ensure thread-safe initialization.

    Returns:
        The singleton ClassifierToolAdapter instance.
    """
    instance = _STATE["instance"]
    if instance is not None:
        return instance

    with _lock:
        # Double-check after acquiring lock
        instance = _STATE["instance"]
        if instance is None:
            instance = create_classifier_adapter()
            _STATE["instance"] = instance

    return instance


def reset_classifier_adapter() -> None:
    """Reset the global classifier adapter singleton (for testing).

    This clears the singleton, allowing a fresh instance to be created
    on the next call to get_classifier_adapter().
    """
    with _lock:
        _STATE["instance"] = None


__all__ = [
    "get_classifier_adapter",
    "reset_classifier_adapter",
]
