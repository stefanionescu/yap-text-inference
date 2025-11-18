"""Sanitization utilities for both user prompts and assistant outputs."""

from __future__ import annotations

import html
import re
import unicodedata

from ..config.filters import (
    BACKSLASH_ESCAPE_PATTERN,
    BLOCKQUOTE_PATTERN,
    CODE_BLOCK_PATTERN,
    EMOJI_PATTERN,
    EMOTICON_PATTERN,
    HEADING_PATTERN,
    HTML_TAG_PATTERN,
    IMAGE_PATTERN,
    INLINE_CODE_PATTERN,
    LINK_PATTERN,
    LIST_MARKER_PATTERN,
    TABLE_BORDER_PATTERN,
)

try:
    from ftfy import fix_text  # type: ignore[import-not-found]
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


def sanitize_llm_output(
    text: str | None,
    *,
    strip_markdown: bool = True,
    strip_emojis: bool = True,
) -> str:
    """Normalize assistant output while keeping semantics intact."""
    if not text:
        return ""

    cleaned = text
    if strip_markdown:
        cleaned = _strip_markdown(cleaned)
    if strip_emojis:
        cleaned = _strip_emojis(cleaned)
    return _normalize_whitespace(cleaned)


def _strip_markdown(text: str) -> str:
    """Convert Markdown-like text into plain text."""
    text = CODE_BLOCK_PATTERN.sub(" ", text)
    text = INLINE_CODE_PATTERN.sub(r"\1", text)
    text = IMAGE_PATTERN.sub(lambda match: match.group(1) or "", text)
    text = LINK_PATTERN.sub(lambda match: match.group(1), text)
    text = HEADING_PATTERN.sub("", text)
    text = BLOCKQUOTE_PATTERN.sub("", text)
    text = LIST_MARKER_PATTERN.sub("", text)
    text = TABLE_BORDER_PATTERN.sub("", text)
    text = text.replace("|", " ")
    text = text.replace("**", "").replace("__", "")
    text = text.replace("*", " ").replace("_", " ")
    text = text.replace("~~", " ")
    text = BACKSLASH_ESCAPE_PATTERN.sub(r"\1", text)
    text = HTML_TAG_PATTERN.sub(" ", text)
    return html.unescape(text)


def _strip_emojis(text: str) -> str:
    """Remove unicode emojis and common ASCII emoticons."""
    text = EMOJI_PATTERN.sub("", text)
    return EMOTICON_PATTERN.sub("", text)


def _normalize_whitespace(text: str) -> str:
    """Collapse redundant whitespace without removing intentional spacing."""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


__all__ = ["sanitize_prompt", "sanitize_llm_output"]
