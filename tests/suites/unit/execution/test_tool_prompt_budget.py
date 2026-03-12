"""Unit tests for exact tool-input budgeting."""

from __future__ import annotations

from typing import Any, cast
from tests.support.helpers.tokenizer import use_local_tokenizers
from src.execution.tool.prompt_budget import fit_tool_input_to_budget


def test_fit_tool_input_to_budget_drops_oldest_history_before_trimming_current_user() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_tool_input_to_budget(
            [
                "check the calendar for next tuesday flight times",
                "show the booking confirmation and hotel address",
            ],
            "open the packing list and weather notes for lisbon",
            tokenizer,
            max_input_tokens=8,
        )

        assert fit.tool_user_history == ""
        assert fit.tool_user_utt == "the packing list and weather notes for lisbon"
        assert fit.input_tokens <= 8


def test_fit_tool_input_to_budget_trims_current_user_when_history_is_exhausted() -> None:
    with use_local_tokenizers() as tokenizer:
        fit = fit_tool_input_to_budget(
            [],
            "check the calendar for next tuesday flight times",
            tokenizer,
            max_input_tokens=4,
        )

        assert fit.tool_user_history == ""
        assert fit.tool_user_utt == "next tuesday flight times"
        assert fit.input_tokens <= 4


def test_fit_tool_input_to_budget_raises_when_budget_is_impossible() -> None:
    with use_local_tokenizers() as tokenizer:
        try:
            fit_tool_input_to_budget(
                ["alpha"],
                "bravo",
                tokenizer,
                max_input_tokens=0,
            )
        except ValueError as exc:
            assert "tool input exceeds exact budget" in str(exc)
        else:
            raise AssertionError("expected ValueError")


class _SpecialAwareTokenizer:
    def count(self, text: str, *, add_special_tokens: bool = False) -> int:
        if not text.strip():
            return 0
        total = len(text.split())
        if add_special_tokens:
            total += 2
        return total

    def trim(self, text: str, max_tokens: int, keep: str = "end") -> str:
        tokens = text.split()
        if max_tokens <= 0:
            return ""
        if len(tokens) <= max_tokens:
            return text
        kept = tokens[:max_tokens] if keep == "start" else tokens[-max_tokens:]
        return " ".join(kept)


def test_fit_tool_input_to_budget_rejects_non_empty_user_that_cannot_fit() -> None:
    tokenizer = cast(Any, _SpecialAwareTokenizer())
    try:
        fit_tool_input_to_budget(
            [],
            "alpha",
            tokenizer,
            max_input_tokens=2,
        )
    except ValueError as exc:
        assert "tool input exceeds exact budget" in str(exc)
    else:
        raise AssertionError("expected ValueError")
