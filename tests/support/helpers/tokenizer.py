"""Shared local tokenizer setup for CPU-only unit tests."""

from __future__ import annotations

import re
from threading import Lock
from typing import Any, cast
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


_PUNCT_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?|[^\w\s]", re.UNICODE)
_ATTACHED_PUNCT = {".", ",", "!", "?", ";", ":", "%", ")", "]", "}"}
_OPENING_PUNCT = {"(", "[", "{", "/", "$", "#"}


class _PunctuationAwareTokenizer:
    def __init__(self) -> None:
        self._vocab: dict[str, int] = {"[BOS]": 0, "[EOS]": 1}
        self._reverse_vocab: dict[int, str] = {0: "[BOS]", 1: "[EOS]"}
        self._next_id = 2

    def _tokenize(self, text: str) -> list[str]:
        return _PUNCT_TOKEN_PATTERN.findall(text)

    def _token_id(self, token: str) -> int:
        token_id = self._vocab.get(token)
        if token_id is None:
            token_id = self._next_id
            self._next_id += 1
            self._vocab[token] = token_id
            self._reverse_vocab[token_id] = token
        return token_id

    def _decode_tokens(self, tokens: list[str]) -> str:
        if not tokens:
            return ""

        out = tokens[0]
        for token in tokens[1:]:
            if token in _ATTACHED_PUNCT or out[-1] in _OPENING_PUNCT:
                out += token
            else:
                out += f" {token}"
        return out

    def count(self, text: str, *, add_special_tokens: bool = False) -> int:
        token_count = len(self._tokenize(text))
        if add_special_tokens:
            return token_count + 2
        return token_count

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        if max_tokens <= 0 or not text:
            return ""
        tokens = self._tokenize(text)
        if len(tokens) <= max_tokens:
            return text.strip()
        kept = tokens[:max_tokens] if keep == "start" else tokens[-max_tokens:]
        return self._decode_tokens(kept)

    def encode_ids(self, text: str) -> list[int]:
        return [self._token_id(token) for token in self._tokenize(text)]

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        add_generation_prompt: bool = True,
        **_template_kwargs: Any,
    ) -> str:
        lines: list[str] = []
        for message in messages:
            lines.extend([f"<|im_start|>{message['role']}", message["content"], "<|im_end|>"])
        if add_generation_prompt:
            lines.append("<|im_start|>assistant")
        return "\n".join(lines)


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


@contextmanager
def use_punctuation_aware_tokenizers() -> Iterator[Any]:
    tokenizer = _PunctuationAwareTokenizer()
    configure_tokenizers(
        chat_tokenizer=cast(Any, tokenizer),
        tool_tokenizer=cast(Any, tokenizer),
    )
    try:
        yield tokenizer
    finally:
        reset_tokenizers()
