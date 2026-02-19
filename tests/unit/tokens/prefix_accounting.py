"""Unit tests for screen-prefix stripping and budget helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.tokens import prefix as token_prefix
from tests.helpers.tokenizer import use_local_tokenizers


def test_strip_screen_prefix_handles_case_insensitive_match() -> None:
    stripped = token_prefix.strip_screen_prefix("check screen: hello", "CHECK SCREEN:", None)
    untouched = token_prefix.strip_screen_prefix("hello there", "CHECK SCREEN:", None)

    assert stripped == "hello"
    assert untouched == "hello there"


def test_get_effective_user_utt_max_tokens_uses_state_and_clamps(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_prefix, "USER_UTT_MAX_TOKENS", 5)
    state = SimpleNamespace(
        check_screen_prefix_tokens=9,
        screen_checked_prefix_tokens=2,
    )

    assert token_prefix.get_effective_user_utt_max_tokens(state, for_followup=False) == 1
    assert token_prefix.get_effective_user_utt_max_tokens(state, for_followup=True) == 3


def test_get_effective_user_utt_max_tokens_without_state_uses_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with use_local_tokenizers():
        monkeypatch.setattr(token_prefix, "DEPLOY_CHAT", True)
        monkeypatch.setattr(token_prefix, "USER_UTT_MAX_TOKENS", 8)
        monkeypatch.setattr(token_prefix, "DEFAULT_CHECK_SCREEN_PREFIX", "check")
        monkeypatch.setattr(token_prefix, "DEFAULT_SCREEN_CHECKED_PREFIX", "screen")

        start_expected = max(1, 8 - token_prefix.count_prefix_tokens("check"))
        followup_expected = max(1, 8 - token_prefix.count_prefix_tokens("screen"))

        assert token_prefix.get_effective_user_utt_max_tokens(None, for_followup=False) == start_expected
        assert token_prefix.get_effective_user_utt_max_tokens(None, for_followup=True) == followup_expected


def test_count_prefix_tokens_returns_zero_when_chat_is_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(token_prefix, "DEPLOY_CHAT", False)

    assert token_prefix.count_prefix_tokens("check") == 0
