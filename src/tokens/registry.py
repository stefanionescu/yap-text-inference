"""Central registry for configured tokenizer runtime dependencies."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .tokenizer import FastTokenizer

_STATE: dict[str, FastTokenizer | None] = {
    "chat_tokenizer": None,
    "tool_tokenizer": None,
}


def configure_tokenizers(
    *,
    chat_tokenizer: FastTokenizer | None,
    tool_tokenizer: FastTokenizer | None,
) -> None:
    """Register process runtime tokenizer instances."""
    _STATE["chat_tokenizer"] = chat_tokenizer
    _STATE["tool_tokenizer"] = tool_tokenizer


def get_chat_tokenizer() -> FastTokenizer:
    """Return configured chat tokenizer."""
    tokenizer = _STATE["chat_tokenizer"]
    if tokenizer is None:
        raise RuntimeError("Chat tokenizer has not been configured in runtime bootstrap")
    return tokenizer


def get_tool_tokenizer() -> FastTokenizer:
    """Return configured tool tokenizer."""
    tokenizer = _STATE["tool_tokenizer"]
    if tokenizer is None:
        raise RuntimeError("Tool tokenizer has not been configured in runtime bootstrap")
    return tokenizer


def reset_tokenizers() -> None:
    """Clear configured tokenizers (for tests/shutdown)."""
    configure_tokenizers(chat_tokenizer=None, tool_tokenizer=None)


__all__ = [
    "configure_tokenizers",
    "get_chat_tokenizer",
    "get_tool_tokenizer",
    "reset_tokenizers",
]
