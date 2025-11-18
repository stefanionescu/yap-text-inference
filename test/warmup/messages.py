from __future__ import annotations

import os
import sys
import random
from typing import List

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from config import WARMUP_FALLBACK_MESSAGE
from config.messages import WARMUP_DEFAULT_MESSAGES


def choose_message(words: List[str]) -> str:
    if words:
        return " ".join(words).strip()
    if WARMUP_DEFAULT_MESSAGES:
        return random.choice(WARMUP_DEFAULT_MESSAGES)
    return WARMUP_FALLBACK_MESSAGE


__all__ = ["choose_message"]

