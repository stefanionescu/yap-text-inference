from __future__ import annotations

import threading
from typing import Optional

from transformers import AutoTokenizer

from .config import CHAT_MODEL


_tokenizer_lock = threading.Lock()
_tokenizer = None


def get_tokenizer():
    global _tokenizer
    if _tokenizer is not None:
        return _tokenizer
    with _tokenizer_lock:
        if _tokenizer is None:
            _tokenizer = AutoTokenizer.from_pretrained(
                CHAT_MODEL,
                use_fast=True,
                trust_remote_code=True,
            )
    return _tokenizer


def exact_token_count(text: str) -> int:
    if not text:
        return 0
    tok = get_tokenizer()
    return len(tok.encode(text, add_special_tokens=False))


def trim_text_to_token_limit_exact(text: str, max_tokens: int, keep: str = "end") -> str:
    if max_tokens <= 0 or not text:
        return ""
    tok = get_tokenizer()
    input_ids = tok.encode(text, add_special_tokens=False)
    if len(input_ids) <= max_tokens:
        return text
    if keep == "start":
        kept = input_ids[:max_tokens]
    else:
        kept = input_ids[-max_tokens:]
    return tok.decode(kept, skip_special_tokens=True, clean_up_tokenization_spaces=True)


