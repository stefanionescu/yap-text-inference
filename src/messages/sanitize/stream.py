"""Streaming sanitizer for assistant outputs.

This sanitizer is stateful and operates on streamed model text. It:
    - Strips freestyle prefixes and leading newline tokens once
    - Verbalizes emails/phone numbers
    - Normalizes ellipses/dashes/quotes/spacing
    - Removes escaped quotes, emojis/emoticons, and HTML tags
    - Enforces a leading capital once
    - Buffers unstable suffixes (ellipsis, partial words/entities) to avoid
      emitting incomplete tokens mid-stream
"""

from __future__ import annotations

import re
import html

from .common import _strip_escaped_quotes
from .suffix import compute_stable_and_tail_lengths
from .verbalize import verbalize_emails, verbalize_phone_numbers
from ...config.filters import (
    EMOJI_PATTERN,
    EMDASH_PATTERN,
    DOT_RUN_PATTERN,
    PERCENT_PATTERN,
    ELLIPSIS_PATTERN,
    EMOTICON_PATTERN,
    HTML_TAG_PATTERN,
    SUBTRACTION_PATTERN,
    TEMP_KELVIN_PATTERN,
    WORD_HYPHEN_PATTERN,
    ACTION_EMOTE_PATTERN,
    TEMP_CELSIUS_PATTERN,
    DEGREE_SYMBOL_PATTERN,
    NEWLINE_TOKEN_PATTERN,
    EXAGGERATED_OH_PATTERN,
    SPACED_DOT_RUN_PATTERN,
    COLLAPSE_SPACES_PATTERN,
    NEGATIVE_NUMBER_PATTERN,
    TEMP_FAHRENHEIT_PATTERN,
    DOUBLE_DOT_SPACE_PATTERN,
    FREESTYLE_PREFIX_PATTERN,
    SPACE_BEFORE_PUNCT_PATTERN,
    SINGLE_LETTER_SUFFIX_PATTERN,
    ELLIPSIS_TRAILING_DOT_PATTERN,
    LEADING_NEWLINE_TOKENS_PATTERN,
    ELLIPSIS_TRAILING_SPACE_PATTERN,
)


class StreamingSanitizer:
    """Stateful sanitizer that emits stable chunks for streaming."""

    # How much suffix (in characters) we keep as a "potentially unstable" buffer
    # so boundary-sensitive validators (emails, phone numbers, ellipsis, html)
    # can operate across streamed chunks.
    _MAX_TAIL = 64

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
        # Whether we've dropped the true stream start from the raw tail window
        self._trimmed_stream_start = False

    def push(self, chunk: str) -> str:
        """Process a new raw chunk and return the sanitized delta."""
        if not chunk:
            return ""

        self._raw_tail += chunk

        prefix_ctx = self._prefix_pending or (not self._trimmed_stream_start)
        capital_ctx = self._capital_pending or (not self._trimmed_stream_start)
        sanitized, prefix_state, capital_state = _sanitize_stream_chunk(
            self._raw_tail,
            prefix_pending=prefix_ctx,
            capital_pending=capital_ctx,
            strip_leading_ws=prefix_ctx,
        )
        self._prefix_pending = prefix_state
        self._capital_pending = capital_state

        stable_len, tail_len = compute_stable_and_tail_lengths(
            raw_tail=self._raw_tail,
            sanitized=sanitized,
            max_tail=self._MAX_TAIL,
        )

        delta = ""
        if stable_len > 0:
            stable = sanitized[:stable_len]
            emitted_text = "".join(self._emitted_parts)
            lcp = _common_prefix_len(emitted_text, stable)
            if lcp < len(emitted_text):
                emitted_text = emitted_text[:lcp]
                self._emitted_parts = [emitted_text] if emitted_text else []
            delta = stable[lcp:]

            if delta:
                self._emitted_parts.append(delta)

        self._sanitized_tail = sanitized[stable_len : stable_len + tail_len]

        return delta

    def flush(self) -> str:
        """Emit any remaining buffered sanitized text."""
        if not self._raw_tail and not self._sanitized_tail:
            return ""

        prefix_ctx = self._prefix_pending or (not self._trimmed_stream_start)
        capital_ctx = self._capital_pending or (not self._trimmed_stream_start)
        sanitized, prefix_state, capital_state = _sanitize_stream_chunk(
            self._raw_tail,
            prefix_pending=prefix_ctx,
            capital_pending=capital_ctx,
            strip_leading_ws=prefix_ctx,
        )
        self._prefix_pending = prefix_state
        self._capital_pending = capital_state

        emitted_text = "".join(self._emitted_parts)
        lcp = _common_prefix_len(emitted_text, sanitized)
        if lcp < len(emitted_text):
            emitted_text = emitted_text[:lcp]
            self._emitted_parts = [emitted_text] if emitted_text else []
        tail = sanitized[lcp:].rstrip()

        if tail:
            self._emitted_parts.append(tail)
        self._sanitized_tail = ""
        self._raw_tail = ""
        self._trimmed_stream_start = False
        return tail

    @property
    def full_text(self) -> str:
        """Return the fully sanitized text accumulated so far."""
        return "".join(self._emitted_parts) + self._sanitized_tail


def _ensure_leading_capital_stream(text: str, capital_pending: bool) -> tuple[str, bool]:
    """Streaming-friendly leading capital enforcement.

    Returns the transformed text and whether capitalization is still pending.
    """
    if not capital_pending:
        return text, False
    for idx, char in enumerate(text):
        if char.isalpha():
            if char.islower():
                return f"{text[:idx]}{char.upper()}{text[idx + 1 :]}", False
            return text, False
    return text, True


def _sanitize_stream_chunk(
    text: str,
    *,
    prefix_pending: bool,
    capital_pending: bool,
    strip_leading_ws: bool,
) -> tuple[str, bool, bool]:
    """Run the streaming sanitization pipeline on a single chunk."""
    if not text:
        return "", prefix_pending, capital_pending

    cleaned = text
    if prefix_pending:
        cleaned = FREESTYLE_PREFIX_PATTERN.sub("", cleaned, count=1)
        if cleaned != text:
            cleaned = cleaned.lstrip()
        cleaned = _strip_leading_newline_tokens(cleaned)
        prefix_pending = False

    # Verbalize emails and phone numbers early (before dash replacement etc.)
    cleaned = verbalize_emails(cleaned)
    cleaned = verbalize_phone_numbers(cleaned)
    cleaned = ACTION_EMOTE_PATTERN.sub("", cleaned)
    cleaned = _strip_asterisks(cleaned)
    cleaned = ELLIPSIS_PATTERN.sub("...", cleaned)
    cleaned = NEWLINE_TOKEN_PATTERN.sub(" ", cleaned)
    cleaned = DOUBLE_DOT_SPACE_PATTERN.sub("...", cleaned)
    cleaned = ELLIPSIS_TRAILING_DOT_PATTERN.sub("...", cleaned)
    # Strip any trailing space after ellipsis
    cleaned = ELLIPSIS_TRAILING_SPACE_PATTERN.sub("...", cleaned)
    # Collapse any run of 4+ dots to ellipsis (preserves "...")
    cleaned = DOT_RUN_PATTERN.sub("...", cleaned)
    # Collapse dots separated by spaces (". . " or ". . .") to a single period
    cleaned = SPACED_DOT_RUN_PATTERN.sub(".", cleaned)
    # Ensure a space after a standalone period if followed by alnum (avoid smushing words)
    # BUT preserve ellipsis: don't add space after "..." followed by text
    cleaned = re.sub(r"(?<!\.)\.(?!\.)(?=[A-Za-z0-9])", ". ", cleaned)
    # Verbalize temperature units before other replacements
    cleaned = TEMP_FAHRENHEIT_PATTERN.sub(" degrees Fahrenheit", cleaned)
    cleaned = TEMP_CELSIUS_PATTERN.sub(" degrees Celsius", cleaned)
    cleaned = TEMP_KELVIN_PATTERN.sub(" degrees Kelvin", cleaned)
    cleaned = DEGREE_SYMBOL_PATTERN.sub(" degrees", cleaned)
    # Verbalize percent sign
    cleaned = PERCENT_PATTERN.sub(" percent", cleaned)
    # Handle dashes/hyphens contextually (order matters: specific → general)
    cleaned = SUBTRACTION_PATTERN.sub(r"\1 minus \2", cleaned)
    cleaned = NEGATIVE_NUMBER_PATTERN.sub(r" minus \1", cleaned)
    # Single-letter suffix: vintage-y → vintagey (no space)
    cleaned = SINGLE_LETTER_SUFFIX_PATTERN.sub(r"\1\2", cleaned)
    # Compound words: well-known → well known (with space)
    cleaned = WORD_HYPHEN_PATTERN.sub(r"\1 \2", cleaned)
    cleaned = EMDASH_PATTERN.sub(" ", cleaned)
    cleaned = cleaned.replace("'", "'")
    cleaned = SPACE_BEFORE_PUNCT_PATTERN.sub(r"\1", cleaned)
    cleaned = _strip_escaped_quotes(cleaned)
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


def _common_prefix_len(a: str, b: str) -> int:
    """Length of the longest common prefix of a and b."""
    max_len = min(len(a), len(b))
    idx = 0
    while idx < max_len and a[idx] == b[idx]:
        idx += 1
    return idx


OH_MAX_O_COUNT = 2
OH_MAX_H_COUNT = 1


def _normalize_exaggerated_oh(match: re.Match[str]) -> str:
    text = match.group(0)
    o_count = sum(1 for char in text if char.lower() == "o")
    h_count = sum(1 for char in text if char.lower() == "h")
    if o_count <= OH_MAX_O_COUNT and h_count <= OH_MAX_H_COUNT:
        return text
    replacement = "Ooh" if text[0].isupper() else "ooh"
    return replacement


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


__all__ = ["StreamingSanitizer"]
