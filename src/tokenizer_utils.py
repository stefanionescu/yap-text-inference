from __future__ import annotations

from threading import Lock
from typing import Optional

from tokenizers import Tokenizer

from .config import CHAT_MODEL


class FastTokenizer:
    def __init__(self, path_or_repo: str):
        # Loads tokenizer.json from local dir or HF repo name (honors HF cache)
        self.tok = Tokenizer.from_pretrained(path_or_repo)
        self._lock = Lock()

    def count(self, text: str) -> int:
        if not text:
            return 0
        with self._lock:
            return self.tok.encode(text).num_tokens

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        if max_tokens <= 0 or not text:
            return ""
        with self._lock:
            enc = self.tok.encode(text)
            ids = enc.ids
            if len(ids) <= max_tokens:
                return text
            if keep == "start":
                kept = ids[:max_tokens]
            else:
                kept = ids[-max_tokens:]
            return self.tok.decode(kept)


_fast_tok: Optional[FastTokenizer] = None
_fast_tok_lock = Lock()


def get_tokenizer() -> FastTokenizer:
    global _fast_tok
    if _fast_tok is not None:
        return _fast_tok
    with _fast_tok_lock:
        if _fast_tok is None:
            _fast_tok = FastTokenizer(CHAT_MODEL)
    return _fast_tok


def exact_token_count(text: str) -> int:
    return get_tokenizer().count(text)


def trim_text_to_token_limit_exact(text: str, max_tokens: int, keep: str = "end") -> str:
    return get_tokenizer().trim(text, max_tokens=max_tokens, keep=keep)


