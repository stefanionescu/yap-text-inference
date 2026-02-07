"""Shared helpers used by prompt and stream sanitizers."""

from __future__ import annotations

from ...config.filters import ESCAPED_QUOTE_PATTERN


def _strip_escaped_quotes(text: str) -> str:
    """Remove escaped quote sequences like \" or \\\" entirely."""
    if not text:
        return ""
    return ESCAPED_QUOTE_PATTERN.sub("", text)


__all__ = ["_strip_escaped_quotes"]
