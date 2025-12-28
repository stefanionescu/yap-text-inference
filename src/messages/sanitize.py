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


class StreamingSanitizer:
    """Stateful sanitizer that emits stable chunks for streaming.

    Complexity: O(len(chunk)) per push. We only ever re-sanitize the
    active tail buffer, never the full history.
    """

    # How much suffix (in characters) we keep as "maybe unstable" to allow
    # boundary-sensitive validators (emails, phone numbers, ellipsis, html).
    _MAX_TAIL = 256

    def __init__(self) -> None:
        # Raw tail retained for boundary-sensitive checks
        self._raw_tail: str = ""
        # Sanitized tail retained but not yet emitted
        self._sanitized_tail: str = ""
        # Sanitized stable parts already emitted
        self._emitted_parts: list[str] = []
        # Flags for one-shot behaviors
        self._prefix_pending = True
        self._capital_pending = True

    def push(self, chunk: str) -> str:
        """Process a new raw chunk and return the sanitized delta."""
        if not chunk:
            return ""

        self._raw_tail += chunk

        sanitized, self._prefix_pending, self._capital_pending = _sanitize_stream_chunk(
            self._raw_tail,
            prefix_pending=self._prefix_pending,
            capital_pending=self._capital_pending,
            strip_leading_ws=self._prefix_pending,
        )

        stable_len, tail_len = _split_stable_and_tail_lengths(
            raw_tail=self._raw_tail,
            sanitized=sanitized,
            max_tail=self._MAX_TAIL,
        )

        delta = ""
        if stable_len > 0:
            stable = sanitized[:stable_len]
            # Avoid re-emitting content that is already in emitted_parts due to tail window overlap
            emitted_text = "".join(self._emitted_parts)
            overlap = _suffix_prefix_overlap(emitted_text, stable, self._MAX_TAIL)
            delta = stable[overlap:]
            if delta:
                self._emitted_parts.append(delta)

        self._sanitized_tail = sanitized[stable_len:stable_len + tail_len]
        # Keep only the raw portion that maps to the retained tail window
        self._raw_tail = self._raw_tail[-self._MAX_TAIL :]

        return delta

    def flush(self) -> str:
        """Emit any remaining buffered sanitized text."""
        if not self._raw_tail and not self._sanitized_tail:
            return ""

        sanitized, self._prefix_pending, self._capital_pending = _sanitize_stream_chunk(
            self._raw_tail,
            prefix_pending=self._prefix_pending,
            capital_pending=self._capital_pending,
            strip_leading_ws=self._prefix_pending,
        )

        # At flush we emit everything and trim trailing whitespace
        tail = sanitized.rstrip()
        self._emitted_parts.append(tail)
        self._sanitized_tail = ""
        self._raw_tail = ""
        return tail

    @property
    def full_text(self) -> str:
        """Return the fully sanitized text accumulated so far."""
        return "".join(self._emitted_parts) + self._sanitized_tail


def _ensure_leading_capital(text: str) -> str:
    """Ensure the first alphabetic character is uppercase."""
    for idx, char in enumerate(text):
        if char.isalpha():
            if char.islower():
                return f"{text[:idx]}{char.upper()}{text[idx + 1:]}"
            break
    return text


def _ensure_leading_capital_stream(text: str, capital_pending: bool) -> tuple[str, bool]:
    """Streaming-friendly leading capital enforcement.

    Returns the transformed text and whether capitalization is still pending.
    """
    if not capital_pending:
        return text, False
    for idx, char in enumerate(text):
        if char.isalpha():
            if char.islower():
                return f"{text[:idx]}{char.upper()}{text[idx + 1:]}", False
            return text, False
    return text, True


def _sanitize_stream_chunk(
    text: str,
    *,
    prefix_pending: bool,
    capital_pending: bool,
    strip_leading_ws: bool,
) -> tuple[str, bool, bool]:
    """Run the streaming sanitization pipeline on a single chunk.

    prefix_pending controls whether freestyle/newline stripping is applied.
    capital_pending controls whether leading-capital enforcement is still needed.
    """
    if not text:
        return "", prefix_pending, capital_pending

    cleaned = text
    if prefix_pending:
        cleaned = FREESTYLE_PREFIX_PATTERN.sub("", cleaned, count=1)
        if cleaned != text:
            cleaned = cleaned.lstrip(": ").lstrip()
        cleaned = _strip_leading_newline_tokens(cleaned)
        prefix_pending = False

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

    cleaned, capital_pending = _ensure_leading_capital_stream(cleaned, capital_pending)

    if strip_leading_ws:
        cleaned = cleaned.lstrip()

    return cleaned, prefix_pending, capital_pending


def _split_stable_and_tail_lengths(
    raw_tail: str,
    sanitized: str,
    max_tail: int,
) -> tuple[int, int]:
    """Compute how much of the sanitized text is stable vs tail to buffer.

    We keep:
    - trailing unstable chars (whitespace, slashes, etc.)
    - trailing partial ellipsis/dots
    - trailing partial html entities (&amp)
    - trailing segments that look like in-progress emails/phone numbers
    """
    if not sanitized:
        return 0, 0

    unstable = _unstable_suffix_len(sanitized)
    html_guard = _html_entity_suffix_len(sanitized)
    email_guard = _email_suffix_len(raw_tail)
    phone_guard = _phone_suffix_len(raw_tail)

    tail_len = min(len(sanitized), max(unstable, html_guard, email_guard, phone_guard, 0))
    stable_len = len(sanitized) - tail_len

    # Bound the retained tail to avoid unbounded buffering
    if tail_len > max_tail:
        stable_len = len(sanitized) - max_tail
        tail_len = max_tail

    return stable_len, tail_len


def _suffix_prefix_overlap(emitted: str, candidate: str, max_check: int) -> int:
    """Return length of the longest suffix of emitted that is a prefix of candidate.

    Only checks up to max_check characters to keep work bounded.
    """
    if not emitted or not candidate:
        return 0
    emitted_suffix = emitted[-max_check:]
    max_len = min(len(emitted_suffix), len(candidate))
    for length in range(max_len, 0, -1):
        if emitted_suffix[-length:] == candidate[:length]:
            return length
    return 0


def _unstable_suffix_len(text: str) -> int:
    idx = len(text)
    while idx > 0 and text[idx - 1] in TRAILING_STREAM_UNSTABLE_CHARS:
        idx -= 1
    # Keep any trailing run of dots (partial ellipsis)
    while idx > 0 and text[idx - 1] == ".":
        idx -= 1
    return len(text) - idx


def _html_entity_suffix_len(text: str) -> int:
    match = re.search(r"&[A-Za-z]{0,10}$", text)
    if not match:
        return 0
    return len(text) - match.start()


def _email_suffix_len(raw_text: str) -> int:
    """Retain trailing text that could still form a valid email across chunks."""
    if not raw_text:
        return 0
    # Common case: if the tail already has a full email, keep nothing extra
    if EMAIL_PATTERN.search(raw_text):
        # Still keep a small guard in case of partial second email
        return min(16, len(raw_text))

    # Partial email guard (local@ or local@domain)
    partial = re.search(r"[A-Za-z0-9._%+-]+@?[A-Za-z0-9.-]*$", raw_text)
    if not partial:
        return 0
    return min(len(raw_text) - partial.start(), 256)


def _phone_suffix_len(raw_text: str) -> int:
    """Retain trailing digits/+/-/spaces that could still form a phone number."""
    if not raw_text:
        return 0
    partial = re.search(r"[+\d][\d \-\(\)]*$", raw_text)
    if not partial:
        return 0
    return min(len(raw_text) - partial.start(), 64)


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
    "StreamingSanitizer",
]

