"""Shared local tokenizer setup for CPU-only unit tests."""

from __future__ import annotations

from threading import Lock
from functools import lru_cache
from collections.abc import Iterator
from contextlib import contextmanager
from src.tokens.tokenizer import FastTokenizer
from tests.config.tokenizer import TEST_TOKENIZER_VOCAB
from src.tokens.registry import reset_tokenizers, configure_tokenizers


class _FakeTransformersTokenizer:
    def __init__(self, vocab: dict[str, int]) -> None:
        self._vocab = vocab
        self._reverse_vocab = {idx: token for token, idx in vocab.items()}
        self._unk_id = vocab["[UNK]"]

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        _ = add_special_tokens
        return [self._vocab.get(token, self._unk_id) for token in text.split()]

    def __call__(
        self,
        text: str,
        *,
        add_special_tokens: bool = False,
        return_attention_mask: bool = False,
        return_token_type_ids: bool = False,
    ) -> dict[str, list[int]]:
        _ = return_attention_mask
        _ = return_token_type_ids
        return {"input_ids": self.encode(text, add_special_tokens=add_special_tokens)}

    def decode(
        self,
        ids: list[int],
        *,
        skip_special_tokens: bool = True,
        clean_up_tokenization_spaces: bool = False,
    ) -> str:
        _ = skip_special_tokens
        _ = clean_up_tokenization_spaces
        return " ".join(self._reverse_vocab.get(token_id, "[UNK]") for token_id in ids)


@lru_cache(maxsize=1)
def _build_test_tokenizer() -> FastTokenizer:
    fast = object.__new__(FastTokenizer)
    fast._lock = Lock()
    fast._hf_tok = _FakeTransformersTokenizer(TEST_TOKENIZER_VOCAB)
    return fast


@contextmanager
def use_local_tokenizers() -> Iterator[FastTokenizer]:
    tokenizer = _build_test_tokenizer()
    configure_tokenizers(chat_tokenizer=tokenizer, tool_tokenizer=tokenizer)
    try:
        yield tokenizer
    finally:
        reset_tokenizers()
