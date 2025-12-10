"""Helpers to compile prompts into token ids for prefix caching."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from ..persona import (
    build_chat_prompt_with_prefix,
    build_chat_warm_prompt,
)
from .tokenizer import get_chat_tokenizer


@dataclass(slots=True)
class CompiledPrompt:
    """Bundle prompt text + its tokenized representation."""

    text: str
    token_ids: list[int]


def compile_chat_prompt(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
    user_utt: str,
) -> CompiledPrompt:
    prompt = build_chat_prompt_with_prefix(static_prefix, runtime_text, history_text, user_utt)
    return CompiledPrompt(prompt, _materialize_chat_ids(prompt))


def compile_chat_warm_prompt(
    static_prefix: str,
    runtime_text: str,
    history_text: str,
) -> CompiledPrompt:
    prompt = build_chat_warm_prompt(static_prefix, runtime_text, history_text)
    return CompiledPrompt(prompt, _materialize_chat_ids(prompt))


@lru_cache(maxsize=512)
def _cached_chat_token_ids(prompt: str) -> tuple[int, ...]:
    tok = get_chat_tokenizer()
    return tuple(tok.encode_ids(prompt))


def _materialize_chat_ids(prompt: str) -> list[int]:
    return list(_cached_chat_token_ids(prompt))


__all__ = [
    "CompiledPrompt",
    "compile_chat_prompt",
    "compile_chat_warm_prompt",
]
