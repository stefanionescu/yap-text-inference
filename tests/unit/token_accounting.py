"""Unit tests for token counting/trimming helpers with a local tokenizer."""

from __future__ import annotations

from src.tokens import utils as token_utils
from tests.unit.local_tokenizer import use_local_tokenizers


def test_count_and_trim_text_with_local_tokenizer() -> None:
    with use_local_tokenizers():
        assert token_utils.count_tokens_chat("a b c") == 3
        assert token_utils.count_tokens_tool("x y") == 2
        assert token_utils.trim_text_to_token_limit_chat("a b c d", max_tokens=2, keep="start") == "a b"
        assert token_utils.trim_text_to_token_limit_tool("a b c d", max_tokens=2, keep="end") == "c d"


def test_build_user_history_for_tool_respects_token_budget() -> None:
    with use_local_tokenizers():
        user_texts = ["one two", "three", "four five six"]
        history = token_utils.build_user_history_for_tool(user_texts, max_tokens=5)
        assert history == "three\nfour five six"


def test_trim_history_preserve_messages_keeps_latest_chunks() -> None:
    with use_local_tokenizers():
        history = "one two three\n\nfour five six\n\nseven eight"
        trimmed = token_utils.trim_history_preserve_messages_chat(history, max_tokens=4)
        assert trimmed == "seven eight"
