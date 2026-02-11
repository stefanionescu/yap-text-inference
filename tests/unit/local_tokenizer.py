"""Shared local tokenizer setup for CPU-only unit tests."""

from __future__ import annotations

from pathlib import Path
from functools import lru_cache
from collections.abc import Iterator
from contextlib import contextmanager

from src.tokens.tokenizer import FastTokenizer
from src.tokens.registry import reset_tokenizers, configure_tokenizers

TOKENIZER_DIR = Path(__file__).resolve().parents[1] / "assets" / "local_tokenizer"


@lru_cache(maxsize=1)
def _load_local_tokenizer() -> FastTokenizer:
    return FastTokenizer(str(TOKENIZER_DIR), load_transformers_tok=False)


@contextmanager
def use_local_tokenizers() -> Iterator[FastTokenizer]:
    tokenizer = _load_local_tokenizer()
    configure_tokenizers(chat_tokenizer=tokenizer, tool_tokenizer=tokenizer)
    try:
        yield tokenizer
    finally:
        reset_tokenizers()
