from __future__ import annotations

from typing import List


def choose_message(words: List[str], fallback: str) -> str:
    if words:
        return " ".join(words).strip()
    return fallback


