from __future__ import annotations

import re

# Heuristic: detect presence of a complete sentence terminator in the stream
_SENTENCE_END_RE = re.compile(r"[.!?](?:[\"”')\]]+)?(?:\s|$)")


def contains_complete_sentence(text: str) -> bool:
    return _SENTENCE_END_RE.search(text) is not None


def has_at_least_n_words(text: str, n: int) -> bool:
    # Whitespace-delimited token count; counts punctuation-attached tokens as words
    return len(text.strip().split()) >= n


