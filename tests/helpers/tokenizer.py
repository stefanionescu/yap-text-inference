"""Shared local tokenizer setup for CPU-only unit tests."""

from __future__ import annotations

from threading import Lock
from functools import lru_cache
from collections.abc import Iterator
from contextlib import contextmanager

from tokenizers import Tokenizer
from tokenizers.models import WordLevel
from tokenizers.pre_tokenizers import Whitespace

from src.tokens.tokenizer import FastTokenizer
from src.tokens.registry import reset_tokenizers, configure_tokenizers

_VOCAB = {
    "[UNK]": 0,
    "SCREEN": 1,
    "Assistant": 2,
    "CHECK": 3,
    "NOW": 4,
    "ON": 5,
    "THE": 6,
    "User": 7,
    "a": 8,
    "a1": 9,
    "a2": 10,
    "a3": 11,
    "alpha": 12,
    "are": 13,
    "b": 14,
    "bravo": 15,
    "c": 16,
    "charlie": 17,
    "d": 18,
    "eight": 19,
    "five": 20,
    "four": 21,
    "great": 22,
    "hello": 23,
    "hi": 24,
    "how": 25,
    "ignored": 26,
    "one": 27,
    "seven": 28,
    "six": 29,
    "three": 30,
    "two": 31,
    "u1": 32,
    "u2": 33,
    "u3": 34,
    "world": 35,
    "x": 36,
    "y": 37,
    "you": 38,
}


@lru_cache(maxsize=1)
def _build_test_tokenizer() -> FastTokenizer:
    tok = Tokenizer(WordLevel(vocab=_VOCAB, unk_token="[UNK]"))  # noqa: S106
    tok.pre_tokenizer = Whitespace()

    fast = object.__new__(FastTokenizer)
    fast._lock = Lock()
    fast.tok = tok
    fast._hf_tok = None
    return fast


@contextmanager
def use_local_tokenizers() -> Iterator[FastTokenizer]:
    tokenizer = _build_test_tokenizer()
    configure_tokenizers(chat_tokenizer=tokenizer, tool_tokenizer=tokenizer)
    try:
        yield tokenizer
    finally:
        reset_tokenizers()
