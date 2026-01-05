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
_chat_tokenizer: FastTokenizer | None = None
_tool_tokenizer: FastTokenizer | None = None

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
    
    global _chat_tokenizer
    if _chat_tokenizer is not None:
        return _chat_tokenizer
    
    with _chat_lock:
        # Double-check after acquiring lock
        if _chat_tokenizer is None:
            if not CHAT_MODEL:
                raise ValueError("CHAT_MODEL is required when DEPLOY_CHAT is True")
            from .tokenizer import FastTokenizer
            _chat_tokenizer = FastTokenizer(CHAT_MODEL)
    
    return _chat_tokenizer


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
    
    global _tool_tokenizer
    if _tool_tokenizer is not None:
        return _tool_tokenizer
    
    with _tool_lock:
        # Double-check after acquiring lock
        if _tool_tokenizer is None:
            if not TOOL_MODEL:
                raise ValueError("TOOL_MODEL is required when DEPLOY_TOOL is True")
            from .tokenizer import FastTokenizer
            _tool_tokenizer = FastTokenizer(TOOL_MODEL)
    
    return _tool_tokenizer


def reset_tokenizers() -> None:
    """Reset all tokenizer singletons (for testing).
    
    Clears both chat and tool tokenizer instances, allowing fresh
    instances to be created on next access.
    """
    global _chat_tokenizer, _tool_tokenizer
    with _chat_lock:
        _chat_tokenizer = None
    with _tool_lock:
        _tool_tokenizer = None


__all__ = [
    "get_chat_tokenizer",
    "get_tool_tokenizer",
    "reset_tokenizers",
]

