"""Regular expression utilities for streaming text analysis.

This module provides heuristics for detecting sentence completion and word
counts in streaming text. Used by StreamTracker to compute time-to-first-
sentence and time-to-first-N-words metrics.
"""

from __future__ import annotations

_TRAILING_CHARS = {'"', "'", ")", "]", "}"}


def contains_complete_sentence(text: str) -> bool:
    """Return True if the text contains a complete sentence terminator."""
    for idx, char in enumerate(text):
        if char not in ".!?":
            continue
        cursor = idx + 1
        while cursor < len(text) and text[cursor] in _TRAILING_CHARS:
            cursor += 1
        if cursor >= len(text) or text[cursor].isspace():
            return True
    return False


def has_at_least_n_words(text: str, n: int) -> bool:
    """Return True if the text contains at least n whitespace-delimited tokens."""
    # Whitespace-delimited token count; counts punctuation-attached tokens as words
    return len(text.strip().split()) >= n


__all__ = ["contains_complete_sentence", "has_at_least_n_words"]
