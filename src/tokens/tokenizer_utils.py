"""Fast tokenization utilities using HuggingFace tokenizers.

This module prefers the ultra-fast `tokenizers` backend when available
(`tokenizer.json` present). For local AWQ output directories that may only
contain classic Transformers tokenizer files (no `tokenizer.json`), it
gracefully falls back to `transformers.AutoTokenizer` while preserving the
same public methods.
"""

from __future__ import annotations

import os
from threading import Lock
from typing import Optional

from tokenizers import Tokenizer

from ..config import CHAT_MODEL


class FastTokenizer:
    def __init__(self, path_or_repo: str):
        """Create a tokenizer optimized for counting/trimming.

        Behavior:
        - If `tokenizer.json` exists at `path_or_repo`, use `tokenizers.Tokenizer`.
        - Otherwise, fall back to `transformers.AutoTokenizer` (fast preferred,
          slow if fast is unavailable). This avoids treating local paths as
          Hugging Face repo IDs.
        """

        self._lock = Lock()
        self.tok: Optional[Tokenizer] = None
        self._hf_tok = None  # transformers tokenizer (fast or slow)

        is_local = False
        try:
            is_local = os.path.exists(path_or_repo)
        except Exception:
            is_local = False

        tokenizer_json_path = os.path.join(path_or_repo, "tokenizer.json") if is_local else None

        if is_local and tokenizer_json_path and os.path.isfile(tokenizer_json_path):
            # Fast path: local folder with tokenizer.json
            self.tok = Tokenizer.from_pretrained(path_or_repo)
            return

        # Fallback: rely on Transformers. Prefer fast; fallback to slow if needed.
        try:
            from transformers import AutoTokenizer  # lazy import
        except Exception as exc:  # pragma: no cover - transformers is a hard dep in this project
            raise RuntimeError(f"Transformers is required for tokenizer fallback: {exc}")

        # Try fast tokenizer first
        try:
            hf_tok = AutoTokenizer.from_pretrained(path_or_repo, use_fast=True, trust_remote_code=True)
            self._hf_tok = hf_tok
            return
        except Exception:
            # Fall back to slow tokenizer
            hf_tok = AutoTokenizer.from_pretrained(path_or_repo, use_fast=False, trust_remote_code=True)
            self._hf_tok = hf_tok

    def count(self, text: str) -> int:
        if not text:
            return 0
        with self._lock:
            if self.tok is not None:
                return self.tok.encode(text).num_tokens
            # transformers fallback (fast or slow)
            try:
                # Avoid adding special tokens to mirror Tokenizer behavior
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                # Some tokenizers prefer the __call__ API
                enc = self._hf_tok(text, add_special_tokens=False, return_attention_mask=False, return_token_type_ids=False)  # type: ignore[call-arg]
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]
            return len(ids)

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        if max_tokens <= 0 or not text:
            return ""
        with self._lock:
            if self.tok is not None:
                enc = self.tok.encode(text)
                ids = enc.ids
                if len(ids) <= max_tokens:
                    return text
                kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
                return self.tok.decode(kept)

            # transformers fallback (fast or slow)
            try:
                ids = self._hf_tok.encode(text, add_special_tokens=False)  # type: ignore[attr-defined]
            except AttributeError:
                enc = self._hf_tok(text, add_special_tokens=False, return_attention_mask=False, return_token_type_ids=False)  # type: ignore[call-arg]
                ids = enc["input_ids"] if isinstance(enc, dict) else enc[0]["input_ids"]

            if len(ids) <= max_tokens:
                return text
            kept = ids[:max_tokens] if keep == "start" else ids[-max_tokens:]
            # Decode without injecting special tokens or cleaning spaces
            return self._hf_tok.decode(kept, skip_special_tokens=True, clean_up_tokenization_spaces=False)  # type: ignore[attr-defined]


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


