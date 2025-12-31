"""Miscellaneous utility functions for test scripts.

This module provides general-purpose helpers that don't fit neatly into
other test helper modules, such as message selection from CLI arguments
or canned defaults.
"""

from __future__ import annotations

import random
from collections.abc import Sequence


def choose_message(
    words: list[str],
    fallback: str,
    *,
    defaults: Sequence[str] | None = None,
    rng: random.Random | None = None,
) -> str:
    """
    Select a message based on user-provided tokens or fallbacks.

    Args:
        words: Tokens captured from CLI/args.
        fallback: Default string used when no tokens/defaults are available.
        defaults: Optional sequence of canned messages to sample from.
        rng: Optional random generator to make deterministic choices in tests.
    """
    if words:
        candidate = " ".join(words).strip()
        if candidate:
            return candidate

    if defaults:
        chooser = rng or random
        return chooser.choice(list(defaults))

    return fallback


__all__ = ["choose_message"]
