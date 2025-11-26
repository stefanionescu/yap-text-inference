"""Sanitization utilities for both user prompts and assistant outputs."""

from __future__ import annotations

import html
import re
import unicodedata

from ..config.filters import (
    BACKSLASH_ESCAPE_PATTERN,
    BLOCKQUOTE_PATTERN,
    CODE_BLOCK_PATTERN,
    DOUBLE_DOT_SPACE_PATTERN,
    ELLIPSIS_PATTERN,
    ELLIPSIS_TRAILING_DOT_PATTERN,
    EMOJI_PATTERN,
    EMOTICON_PATTERN,
    ESCAPED_QUOTE_PATTERN,
    EXAGGERATED_OH_PATTERN,
    FREESTYLE_PREFIX_PATTERN,
    FREESTYLE_TARGET_PREFIXES,
    HEADING_PATTERN,
    HTML_TAG_PATTERN,
    IMAGE_PATTERN,
    INLINE_CODE_PATTERN,
    LINK_PATTERN,
    LIST_MARKER_PATTERN,
    NEWLINE_TOKEN_PATTERN,
    TABLE_BORDER_PATTERN,
    TRAILING_STREAM_UNSTABLE_CHARS,
)
from ..config.limits import PROMPT_SANITIZE_MAX_CHARS

try:
    from ftfy import fix_text  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - ftfy is declared in requirements
    def fix_text(text: str) -> str:  # type: ignore
        return text


_CTRL_RE = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]")
_BIDI_RE = re.compile(r"[\u202A-\u202E\u2066-\u2069\u200E\u200F\u061C]")


def sanitize_prompt(raw: str | None, max_chars: int = PROMPT_SANITIZE_MAX_CHARS) -> str:
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
) -> str:
    """Normalize assistant output while keeping semantics intact."""
    if not text:
        return ""

    cleaned = text
    if strip_markdown:
        cleaned = _strip_markdown(cleaned)
    return _normalize_whitespace(cleaned)


def sanitize_stream_text(text: str) -> str:
    """Apply lightweight sanitization suitable for live streaming."""
    if not text:
        return ""
    cleaned = FREESTYLE_PREFIX_PATTERN.sub("", text, count=1)
    if cleaned != text:
        cleaned = cleaned.lstrip(": ").lstrip()
    cleaned = ELLIPSIS_PATTERN.sub("...", cleaned)
    cleaned = NEWLINE_TOKEN_PATTERN.sub(" ", cleaned)
    cleaned = DOUBLE_DOT_SPACE_PATTERN.sub("...", cleaned)
    cleaned = ELLIPSIS_TRAILING_DOT_PATTERN.sub("...", cleaned)
    cleaned = cleaned.replace("'", "'")
    cleaned = re.sub(r"\s+([',?!])", r"\1", cleaned)
    cleaned = ESCAPED_QUOTE_PATTERN.sub(_normalize_escaped_quote, cleaned)
    cleaned = EXAGGERATED_OH_PATTERN.sub(_normalize_exaggerated_oh, cleaned)
    cleaned = _strip_emoji_like_tokens(cleaned)
    # Strip HTML tags and unescape entities
    cleaned = HTML_TAG_PATTERN.sub("", cleaned)
    cleaned = html.unescape(cleaned)
    return _ensure_leading_capital(cleaned)


class StreamingSanitizer:
    """Stateful sanitizer that emits stable chunks for streaming."""

    def __init__(self) -> None:
        self._raw: str = ""
        self._emitted_len: int = 0
        self._last_sanitized: str = ""

    def push(self, chunk: str) -> str:
        """Process a new raw chunk and return the sanitized delta."""
        if not chunk:
            return ""
        self._raw += chunk
        sanitized = self._sanitize()
        if _is_prefix_pending(self._raw):
            return ""
        stable_len = _stable_length(sanitized)
        if stable_len <= self._emitted_len:
            return ""
        delta = sanitized[self._emitted_len:stable_len]
        self._emitted_len = stable_len
        return delta

    def flush(self) -> str:
        """Return any remaining buffered sanitized text."""
        if not self._raw:
            return ""
        sanitized = self._last_sanitized or self._sanitize()
        if _is_prefix_pending(self._raw):
            return ""
        if len(sanitized) <= self._emitted_len:
            return ""
        tail = sanitized[self._emitted_len:]
        self._emitted_len = len(sanitized)
        return tail

    @property
    def full_text(self) -> str:
        """Return the fully sanitized text accumulated so far."""
        return self._last_sanitized or self._sanitize()

    def _sanitize(self) -> str:
        sanitized = sanitize_stream_text(self._raw)
        self._last_sanitized = sanitized
        return sanitized


def _is_prefix_pending(raw_text: str) -> bool:
    stripped = raw_text.lstrip()
    if not stripped:
        return True
    lowered = stripped.lower()
    for target in FREESTYLE_TARGET_PREFIXES:
        if lowered.startswith(target):
            return False
        if len(lowered) < len(target) and target.startswith(lowered):
            return True
    return False


def _stable_length(text: str) -> int:
    idx = len(text)
    while idx > 0 and text[idx - 1] in TRAILING_STREAM_UNSTABLE_CHARS:
        idx -= 1
    return idx


def _ensure_leading_capital(text: str) -> str:
    """Ensure the first alphabetic character is uppercase."""
    for idx, char in enumerate(text):
        if char.isalpha():
            if char.islower():
                return f"{text[:idx]}{char.upper()}{text[idx + 1:]}"
            break
    return text


def _normalize_exaggerated_oh(match: re.Match[str]) -> str:
    text = match.group(0)
    o_count = sum(1 for char in text if char.lower() == "o")
    h_count = sum(1 for char in text if char.lower() == "h")
    if o_count <= 2 and h_count <= 1:
        return text
    replacement = "Ooh" if text[0].isupper() else "ooh"
    return replacement


def _normalize_escaped_quote(match: re.Match[str]) -> str:
    """Replace escaped quotes, downgrading \" to ' for stability."""
    char = match.group(1)
    if char == '"':
        return "'"
    return char


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


def _strip_emoji_like_tokens(text: str) -> str:
    """Remove unicode emojis and ASCII emoticons while collapsing spacing."""
    if not text:
        return ""
    text = EMOJI_PATTERN.sub(" ", text)
    text = EMOTICON_PATTERN.sub(" ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text


def _normalize_whitespace(text: str) -> str:
    """Collapse redundant whitespace without removing intentional spacing."""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s{2,}", " ", text)
    return text.strip()


__all__ = [
    "sanitize_prompt",
    "sanitize_llm_output",
    "sanitize_stream_text",
    "StreamingSanitizer",
]
