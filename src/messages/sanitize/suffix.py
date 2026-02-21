"""Suffix length detection for streaming stability.

This module computes how much of a streaming text suffix should be
buffered to avoid emitting incomplete patterns:

- Trailing unstable characters (partial words, ellipsis)
- Partial HTML entities (&amp;)
- Unclosed HTML tags (<div)
- Partial email addresses (user@domain)
- Partial phone numbers (+1 234)

By retaining these suffixes, the StreamingSanitizer can process
boundary-sensitive patterns across chunk boundaries.
"""

from __future__ import annotations

import re
from ...config.filters import EMAIL_PATTERN, TRAILING_STREAM_UNSTABLE_CHARS


def unstable_suffix_len(text: str) -> int:
    """Compute length of trailing unstable characters.

    Includes trailing whitespace, partial ellipsis (dots), and other
    characters that may change when more text arrives.
    """
    idx = len(text)
    while idx > 0 and text[idx - 1] in TRAILING_STREAM_UNSTABLE_CHARS:
        idx -= 1
    # Keep any trailing run of dots (partial ellipsis)
    while idx > 0 and text[idx - 1] == ".":
        idx -= 1
    return len(text) - idx


def html_entity_suffix_len(text: str) -> int:
    """Compute length of partial HTML entity at end.

    Matches patterns like "&amp" (incomplete entity).
    """
    match = re.search(r"&[A-Za-z]{0,10}$", text)
    if not match:
        return 0
    return len(text) - match.start()


def html_tag_suffix_len(raw_text: str) -> int:
    """Compute length to retain if last '<' is not closed.

    Returns 0 if:
    - The last '<' has a matching '>' after it
    - The '<' is followed by a digit (e.g., '<3' heart emoticon, not a tag)
    """
    if not raw_text:
        return 0
    last_lt = raw_text.rfind("<")
    if last_lt == -1:
        return 0
    last_gt = raw_text.rfind(">")
    if last_gt > last_lt:
        return 0
    # '<' followed by digit is not an HTML tag (e.g., '<3' heart emoticon)
    if last_lt + 1 < len(raw_text) and raw_text[last_lt + 1].isdigit():
        return 0
    return min(len(raw_text) - last_lt, 256)


def email_suffix_len(raw_text: str) -> int:
    """Compute length to retain for partial email detection.

    Keeps trailing characters that could form a valid email
    across chunk boundaries.
    """
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


def phone_suffix_len(raw_text: str) -> int:
    """Compute length to retain for partial phone number detection.

    Keeps trailing digits/+/-/spaces that could form a phone number.
    """
    if not raw_text:
        return 0
    partial = re.search(r"[+\d][\d \-\(\)]*$", raw_text)
    if not partial:
        return 0
    return min(len(raw_text) - partial.start(), 64)


def emoticon_suffix_len(text: str) -> int:
    """Compute length to retain for partial emoticon detection.

    Keeps trailing characters that could form a complete emoticon
    across chunk boundaries. This prevents emitting partial emoticons
    like ':' or ':-' that should be stripped when completed as ':-)'
    """
    if not text:
        return 0
    # Match potential partial emoticons at end of text:
    # - Eyes only: : = ; 8
    # - Eyes + nose: :- ;- =- :^ ;^ =^
    # - Eyes + space (could be followed by emoticon): " :"
    # - Potential heart: <
    # - Potential XD: X or x at end
    partial = re.search(
        r"(?:"
        r"[:=;8][-^]?|"  # Eyes with optional nose (no mouth yet)
        r"<|"  # Potential heart <3
        r"[xX](?![a-zA-Z])|"  # Potential XD
        r"\^_?|"  # Potential ^_^
        r"[tT]_?"  # Potential T_T
        r")$",
        text,
    )
    if not partial:
        return 0
    return len(text) - partial.start()


def compute_stable_and_tail_lengths(
    raw_tail: str,
    sanitized: str,
    max_tail: int,
) -> tuple[int, int]:
    """Compute how much of the sanitized text is stable vs tail to buffer.

    Returns (stable_len, tail_len) where:
    - stable_len: Characters safe to emit
    - tail_len: Characters to buffer for next chunk
    """
    if not sanitized:
        return 0, 0

    unstable = unstable_suffix_len(sanitized)
    html_guard = html_entity_suffix_len(sanitized)
    html_tag_guard = html_tag_suffix_len(raw_tail)
    email_guard = email_suffix_len(raw_tail)
    phone_guard = phone_suffix_len(raw_tail)
    emoticon_guard = emoticon_suffix_len(raw_tail)

    tail_len = min(
        len(sanitized),
        max(unstable, html_guard, html_tag_guard, email_guard, phone_guard, emoticon_guard, 0),
    )
    stable_len = len(sanitized) - tail_len

    # Bound the retained tail to avoid unbounded buffering
    if tail_len > max_tail:
        stable_len = len(sanitized) - max_tail
        tail_len = max_tail

    return stable_len, tail_len


__all__ = [
    "unstable_suffix_len",
    "html_entity_suffix_len",
    "html_tag_suffix_len",
    "email_suffix_len",
    "phone_suffix_len",
    "emoticon_suffix_len",
    "compute_stable_and_tail_lengths",
]
