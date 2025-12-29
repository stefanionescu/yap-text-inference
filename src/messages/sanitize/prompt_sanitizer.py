"""Prompt sanitization utilities for user-provided text.

This module performs a one-shot cleanup of inbound prompts:
    - Type validation and non-empty enforcement
    - Unicode normalization (NFKC) and mojibake repair
    - Control and bidi character stripping
    - Escaped quote stripping
    - Size limiting
"""

from __future__ import annotations

import unicodedata

from ...config.filters import BIDI_CHAR_PATTERN, CTRL_CHAR_PATTERN
from ...config.limits import PROMPT_SANITIZE_MAX_CHARS
from .common import _strip_escaped_quotes

try:
    from ftfy import fix_text  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - ftfy is declared in requirements
    def fix_text(text: str) -> str:  # type: ignore
        """Fallback when ftfy is not available."""
        return text


def sanitize_prompt(raw: str | None, max_chars: int = PROMPT_SANITIZE_MAX_CHARS) -> str:
    """Sanitize user-provided prompt text."""
    if raw is None:
        raise ValueError("prompt is required")
    if not isinstance(raw, str):
        raise ValueError("prompt must be a string")

    # Normalize and fix encoding issues
    text = fix_text(raw)
    text = unicodedata.normalize("NFKC", text)

    # Remove disallowed controls, bidi markers, and escaped quotes
    text = CTRL_CHAR_PATTERN.sub("", text)
    text = BIDI_CHAR_PATTERN.sub("", text)
    text = _strip_escaped_quotes(text)

    text = text.strip()
    if not text:
        raise ValueError("prompt is empty after sanitization")
    if len(text) > max_chars:
        raise ValueError("prompt too large")
    return text


class PromptSanitizer:
    """One-shot prompt sanitizer kept stateful for API symmetry with streaming."""

    def __init__(self, max_chars: int = PROMPT_SANITIZE_MAX_CHARS) -> None:
        self.max_chars = max_chars

    def sanitize(self, raw: str | None) -> str:
        """Sanitize user prompt with the configured max_chars."""
        return sanitize_prompt(raw, max_chars=self.max_chars)

    def __call__(self, raw: str | None) -> str:
        """Allow instances to be invoked like a function."""
        return self.sanitize(raw)


__all__ = ["sanitize_prompt", "PromptSanitizer"]

