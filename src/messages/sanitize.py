"""Sanitization utilities for both user prompts and assistant outputs.

This module provides text sanitization at two levels:

1. User Prompt Sanitization (sanitize_prompt):
   - Input validation and type checking
   - Unicode normalization (NFKC)
   - Mojibake repair via ftfy
   - Control character removal
   - Bidi direction marker removal
   - Size limit enforcement

2. Streaming Output Sanitization (StreamingSanitizer):
   - Stateful processing for live streaming
   - Freestyle prefix stripping
   - Ellipsis normalization
   - Quote normalization
   - Emoji/emoticon removal
   - HTML tag stripping
   - Capital letter enforcement

The StreamingSanitizer is designed for live streaming where text may
be incomplete. It buffers "unstable" trailing characters (ellipsis,
partial words) until more context arrives, ensuring clean output.
"""

from __future__ import annotations

import html
import re
import unicodedata

from ..config.filters import (
    BIDI_CHAR_PATTERN,
    COLLAPSE_SPACES_PATTERN,
    CTRL_CHAR_PATTERN,
    DASH_PATTERN,
    DIGIT_WORDS,
    DOUBLE_DOT_SPACE_PATTERN,
    ELLIPSIS_PATTERN,
    ELLIPSIS_TRAILING_DOT_PATTERN,
    ELLIPSIS_TRAILING_SPACE_PATTERN,
    EMAIL_PATTERN,
    EMOJI_PATTERN,
    EMOTICON_PATTERN,
    ESCAPED_QUOTE_PATTERN,
    EXAGGERATED_OH_PATTERN,
    FREESTYLE_PREFIX_PATTERN,
    FREESTYLE_TARGET_PREFIXES,
    HTML_TAG_PATTERN,
    LEADING_NEWLINE_TOKENS_PATTERN,
    NEWLINE_TOKEN_PATTERN,
    SPACE_BEFORE_PUNCT_PATTERN,
    TRAILING_STREAM_UNSTABLE_CHARS,
)
from ..config.limits import PROMPT_SANITIZE_MAX_CHARS

from phonenumbers import PhoneNumberMatcher  # type: ignore[import-untyped]

try:
    from ftfy import fix_text  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - ftfy is declared in requirements
    def fix_text(text: str) -> str:  # type: ignore
        """Fallback when ftfy is not available."""
        return text


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
    text = CTRL_CHAR_PATTERN.sub("", text)
    text = BIDI_CHAR_PATTERN.sub("", text)

    text = text.strip()
    if not text:
        raise ValueError("prompt is empty after sanitization")
    if len(text) > max_chars:
        raise ValueError("prompt too large")
    return text


def sanitize_stream_text(text: str) -> str:
    """Apply lightweight sanitization suitable for live streaming."""
    if not text:
        return ""
    cleaned = FREESTYLE_PREFIX_PATTERN.sub("", text, count=1)
    if cleaned != text:
        cleaned = cleaned.lstrip(": ").lstrip()
    cleaned = _strip_leading_newline_tokens(cleaned)
    # Verbalize emails and phone numbers early (before dash replacement etc.)
    cleaned = _verbalize_emails(cleaned)
    cleaned = _verbalize_phone_numbers(cleaned)
    cleaned = _strip_asterisks(cleaned)
    cleaned = ELLIPSIS_PATTERN.sub("...", cleaned)
    cleaned = NEWLINE_TOKEN_PATTERN.sub(" ", cleaned)
    cleaned = DOUBLE_DOT_SPACE_PATTERN.sub("...", cleaned)
    cleaned = ELLIPSIS_TRAILING_DOT_PATTERN.sub("...", cleaned)
    # Strip any trailing space after ellipsis
    cleaned = ELLIPSIS_TRAILING_SPACE_PATTERN.sub("...", cleaned)
    # Replace dashes/hyphens with space (before space collapsing)
    cleaned = DASH_PATTERN.sub(" ", cleaned)
    cleaned = cleaned.replace("'", "'")
    cleaned = SPACE_BEFORE_PUNCT_PATTERN.sub(r"\1", cleaned)
    cleaned = ESCAPED_QUOTE_PATTERN.sub(_normalize_escaped_quote, cleaned)
    cleaned = EXAGGERATED_OH_PATTERN.sub(_normalize_exaggerated_oh, cleaned)
    cleaned = _strip_emoji_like_tokens(cleaned)
    # Strip HTML tags and unescape entities
    cleaned = HTML_TAG_PATTERN.sub("", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = _collapse_spaces(cleaned)
    cleaned = _ensure_leading_capital(cleaned)
    # Strip leading whitespace so output always starts with letter/digit
    return cleaned.lstrip()


class StreamingSanitizer:
    """Stateful sanitizer that emits stable chunks for streaming.
    
    This class accumulates raw text and emits sanitized deltas, holding
    back "unstable" trailing characters that might change with more context.
    
    Example:
        sanitizer = StreamingSanitizer()
        for chunk in raw_stream:
            clean = sanitizer.push(chunk)
            if clean:
                send_to_client(clean)
        # Flush any remaining buffered text
        tail = sanitizer.flush()
        if tail:
            send_to_client(tail)
    
    Attributes:
        _raw: Accumulated raw text.
        _emitted_len: Length of sanitized text already emitted.
        _last_sanitized: Cached result of last sanitization.
    """

    def __init__(self) -> None:
        self._raw: str = ""
        self._emitted_len: int = 0
        self._last_sanitized: str = ""

    def push(self, chunk: str) -> str:
        """Process a new raw chunk and return the sanitized delta.
        
        Accumulates the chunk, re-sanitizes the full text, and returns
        only the new stable portion not yet emitted.
        
        Args:
            chunk: New raw text chunk from the model.
            
        Returns:
            Sanitized delta to emit, or empty string if none stable.
        """
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


def _strip_leading_newline_tokens(text: str) -> str:
    """Remove leading newline tokens without inserting padding."""
    if not text:
        return ""
    return LEADING_NEWLINE_TOKENS_PATTERN.sub("", text)


def _collapse_spaces(text: str) -> str:
    """Collapse runs of spaces/tabs into a single space."""
    if not text:
        return ""
    return COLLAPSE_SPACES_PATTERN.sub(" ", text)


def _strip_asterisks(text: str) -> str:
    """Remove asterisk markers used for emphasis."""
    if not text:
        return ""
    return text.replace("*", " ")


def _strip_emoji_like_tokens(text: str) -> str:
    """Remove unicode emojis and ASCII emoticons while collapsing spacing."""
    if not text:
        return ""
    text = EMOJI_PATTERN.sub(" ", text)
    text = EMOTICON_PATTERN.sub(" ", text)
    return _collapse_spaces(text)


def _verbalize_email(email: str) -> str:
    """Convert email to spoken form: me@you.com → me at you dot com."""
    result = email.replace("@", " at ")
    result = result.replace(".", " dot ")
    return result


def _verbalize_emails(text: str) -> str:
    """Find and verbalize all email addresses in text."""
    if not text:
        return ""

    def replace_email(match: re.Match[str]) -> str:
        return _verbalize_email(match.group(0))

    return EMAIL_PATTERN.sub(replace_email, text)


def _verbalize_phone_digit(char: str) -> str:
    """Convert a single phone character to spoken form."""
    if char == "+":
        return "plus"
    if char in DIGIT_WORDS:
        return DIGIT_WORDS[char]
    return ""


def _verbalize_phone_number(raw_number: str) -> str:
    """Convert phone number to spoken form: +1 234 → plus one two three four."""
    words: list[str] = []
    for char in raw_number:
        word = _verbalize_phone_digit(char)
        if word:
            words.append(word)
    return " ".join(words)


def _verbalize_phone_numbers(text: str) -> str:
    """Find and verbalize phone numbers with international format (+XX...).
    
    Only detects numbers with explicit country code (e.g., +1, +44).
    Local numbers without + prefix are not considered phone numbers.
    """
    if not text:
        return text

    matches: list[tuple[int, int, str]] = []

    # region=None only matches international format with explicit + country code
    for match in PhoneNumberMatcher(text, None):
        matches.append((match.start, match.end, _verbalize_phone_number(match.raw_string)))

    if not matches:
        return text

    # Replace from end to start to preserve positions
    matches.sort(key=lambda x: x[0], reverse=True)
    result = text
    for start, end, verbalized in matches:
        result = result[:start] + verbalized + result[end:]

    return result


__all__ = [
    "sanitize_prompt",
    "sanitize_stream_text",
    "StreamingSanitizer",
]

