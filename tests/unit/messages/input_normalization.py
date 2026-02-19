"""Unit tests for input normalization helpers."""

from __future__ import annotations

from src.messages.input import (
    normalize_gender,
    normalize_personality,
    is_gender_empty_or_null,
    is_personality_empty_or_null,
)

# --- normalize_gender ---


def test_normalize_gender_none() -> None:
    assert normalize_gender(None) is None


def test_normalize_gender_female() -> None:
    assert normalize_gender("female") == "female"


def test_normalize_gender_female_titlecase() -> None:
    assert normalize_gender("Female") == "female"


def test_normalize_gender_male_uppercase() -> None:
    assert normalize_gender("MALE") == "male"


def test_normalize_gender_invalid() -> None:
    assert normalize_gender("other") is None


def test_normalize_gender_strips_whitespace() -> None:
    assert normalize_gender("  male  ") == "male"


# --- is_gender_empty_or_null ---


def test_is_gender_empty_or_null_none() -> None:
    assert is_gender_empty_or_null(None) is True


def test_is_gender_empty_or_null_empty() -> None:
    assert is_gender_empty_or_null("") is True


def test_is_gender_empty_or_null_valid() -> None:
    assert is_gender_empty_or_null("female") is False


# --- normalize_personality ---


def test_normalize_personality_none() -> None:
    assert normalize_personality(None) is None


def test_normalize_personality_empty() -> None:
    assert normalize_personality("") is None


def test_normalize_personality_valid() -> None:
    assert normalize_personality("warm") == "warm"


def test_normalize_personality_uppercase() -> None:
    assert normalize_personality("WARM") == "warm"


def test_normalize_personality_digits() -> None:
    assert normalize_personality("123") is None


def test_normalize_personality_too_long() -> None:
    assert normalize_personality("a" * 200) is None


# --- is_personality_empty_or_null ---


def test_is_personality_empty_or_null_none() -> None:
    assert is_personality_empty_or_null(None) is True


def test_is_personality_empty_or_null_empty() -> None:
    assert is_personality_empty_or_null("") is True


def test_is_personality_empty_or_null_valid() -> None:
    assert is_personality_empty_or_null("warm") is False
