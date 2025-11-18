"""Prompt sanitization utilities.

Performs conservative, content-preserving sanitization suitable for LLM prompts:
- Unicode normalization and fixing (ftfy)
- Removal of control characters (except TAB/CR/LF)
- Removal of bidi/invisible directional controls

Note: We intentionally do not HTML-escape or strip symbols like angle brackets or
JSON punctuation to avoid altering prompt semantics.
"""

from __future__ import annotations

import re
import unicodedata

try:
    from ftfy import fix_text
except Exception:  # pragma: no cover - ftfy is declared in requirements
    def fix_text(text: str) -> str:  # type: ignore
        return text


_CTRL_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
_BIDI_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069\u200E\u200F\u061C]")


def sanitize_prompt(raw: str | None, max_chars: int = 200_000) -> str:
    """Sanitize user-provided prompt text.

    - Ensures type is string and non-empty after trimming
    - Normalizes Unicode and fixes mojibake
    - Removes control characters (except TAB/CR/LF)
    - Removes bidi direction control characters

    Args:
        raw: Raw input text
        max_chars: Maximum allowed character length after sanitization

    Returns:
        Sanitized text

    Raises:
        ValueError: If invalid type, empty after cleaning, or exceeds size limit
    """
    if raw is None:
        raise ValueError("prompt is required")
    if not isinstance(raw, str):
        raise ValueError("prompt must be a string")

    # Normalize and fix encoding issues
    text = fix_text(raw)
    text = unicodedata.normalize("NFKC", text)

    # Remove disallowed controls and bidi markers
    text = _CTRL_RE.sub("", text)
    text = _BIDI_RE.sub("", text)

    text = text.strip()
    if not text:
        raise ValueError("prompt is empty after sanitization")
    if len(text) > max_chars:
        raise ValueError("prompt too large")
    return text


