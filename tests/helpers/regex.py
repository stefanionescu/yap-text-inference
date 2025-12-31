"""Regular expression utilities for streaming text analysis.

This module provides heuristics for detecting sentence completion and word
counts in streaming text. Used by StreamTracker to compute time-to-first-
sentence and time-to-first-N-words metrics.
"""

from __future__ import annotations

import re

# Heuristic: detect presence of a complete sentence terminator in the stream
_SENTENCE_END_RE = re.compile(r'''[.!?](?:["')\]]+)?(?:\s|$)''')


def contains_complete_sentence(text: str) -> bool:
    """Return True if the text contains a complete sentence terminator."""
    return _SENTENCE_END_RE.search(text) is not None


def has_at_least_n_words(text: str, n: int) -> bool:
    """Return True if the text contains at least n whitespace-delimited tokens."""
    # Whitespace-delimited token count; counts punctuation-attached tokens as words
    return len(text.strip().split()) >= n


__all__ = ["contains_complete_sentence", "has_at_least_n_words"]
