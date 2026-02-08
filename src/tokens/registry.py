"""Central registry for tokenizer singleton instances.

This module owns all tokenizer singleton instances, providing a single location
for lifecycle management. Entry-point code accesses tokenizers through this
registry; other modules receive tokenizer instances as parameters where possible.

The registry uses lazy initialization with thread-safe locking - tokenizers
are created on first access, not at import time.

Usage:
    from src.tokens.registry import get_chat_tokenizer, get_tool_tokenizer

    tokenizer = get_chat_tokenizer()
    count = tokenizer.count(text)
"""

from __future__ import annotations

from threading import Lock
from typing import TYPE_CHECKING

from ..config import CHAT_MODEL, TOOL_MODEL, DEPLOY_CHAT, DEPLOY_TOOL

if TYPE_CHECKING:
    from .tokenizer import FastTokenizer

# Singleton instances - created lazily on first access
_STATE: dict[str, FastTokenizer | None] = {"chat": None, "tool": None}

# Thread-safe locks for initialization
_chat_lock = Lock()
_tool_lock = Lock()


def get_chat_tokenizer() -> FastTokenizer:
    """Get the chat model tokenizer singleton.

    Lazily initializes the tokenizer on first access using CHAT_MODEL config.
    Thread-safe via double-checked locking.

    Returns:
        FastTokenizer instance for the chat model.

    Raises:
        RuntimeError: If DEPLOY_CHAT is False.
        ValueError: If CHAT_MODEL is not configured.
    """
    if not DEPLOY_CHAT:
        raise RuntimeError("get_chat_tokenizer() called but DEPLOY_CHAT is False")

    tokenizer = _STATE["chat"]
    if tokenizer is not None:
        return tokenizer

    with _chat_lock:
        # Double-check after acquiring lock
        tokenizer = _STATE["chat"]
        if tokenizer is None:
            if not CHAT_MODEL:
                raise ValueError("CHAT_MODEL is required when DEPLOY_CHAT is True")
            from .tokenizer import FastTokenizer  # noqa: PLC0415

            tokenizer = FastTokenizer(CHAT_MODEL)
            _STATE["chat"] = tokenizer

    return tokenizer


def get_tool_tokenizer() -> FastTokenizer:
    """Get the tool model tokenizer singleton.

    Lazily initializes the tokenizer on first access using TOOL_MODEL config.
    Thread-safe via double-checked locking.

    Returns:
        FastTokenizer instance for the tool model.

    Raises:
        RuntimeError: If DEPLOY_TOOL is False.
        ValueError: If TOOL_MODEL is not configured.
    """
    if not DEPLOY_TOOL:
        raise RuntimeError("get_tool_tokenizer() called but DEPLOY_TOOL is False")

    tokenizer = _STATE["tool"]
    if tokenizer is not None:
        return tokenizer

    with _tool_lock:
        # Double-check after acquiring lock
        tokenizer = _STATE["tool"]
        if tokenizer is None:
            if not TOOL_MODEL:
                raise ValueError("TOOL_MODEL is required when DEPLOY_TOOL is True")
            from .tokenizer import FastTokenizer  # noqa: PLC0415

            tokenizer = FastTokenizer(TOOL_MODEL)
            _STATE["tool"] = tokenizer

    return tokenizer


def reset_tokenizers() -> None:
    """Reset all tokenizer singletons (for testing).

    Clears both chat and tool tokenizer instances, allowing fresh
    instances to be created on next access.
    """
    with _chat_lock:
        _STATE["chat"] = None
    with _tool_lock:
        _STATE["tool"] = None


__all__ = [
    "get_chat_tokenizer",
    "get_tool_tokenizer",
    "reset_tokenizers",
]
