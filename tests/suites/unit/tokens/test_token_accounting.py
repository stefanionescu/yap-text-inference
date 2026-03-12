"""Unit tests for token counting/trimming helpers with a local tokenizer."""

from __future__ import annotations

from src.tokens import utils as token_utils
from tests.support.helpers.tokenizer import use_local_tokenizers


def test_count_and_trim_text_with_local_tokenizer() -> None:
    with use_local_tokenizers():
        assert token_utils.count_tokens_chat("a b c") == 3
        assert token_utils.count_tokens_tool("x y") == 2
        assert token_utils.trim_text_to_token_limit_chat("a b c d", max_tokens=2, keep="start") == "a b"
        assert token_utils.trim_text_to_token_limit_tool("a b c d", max_tokens=2, keep="end") == "c d"


def test_build_user_history_for_tool_respects_token_budget() -> None:
    with use_local_tokenizers():
        user_texts = [
            "check the calendar for next tuesday flight times",
            "show the booking confirmation and hotel address",
            "open the packing list and weather notes for lisbon",
        ]
        history = token_utils.build_user_history_for_tool(user_texts, max_tokens=8)
        assert history == "the packing list and weather notes for lisbon"


def test_build_user_history_for_tool_trims_single_oversized_latest_message() -> None:
    with use_local_tokenizers():
        history = token_utils.build_user_history_for_tool(
            ["check the calendar for next tuesday flight times"],
            max_tokens=4,
        )
        assert history == "next tuesday flight times"
        assert token_utils.count_tokens_tool(history) == 4
