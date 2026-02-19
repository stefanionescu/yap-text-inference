"""Unit tests for email and phone verbalization."""

from __future__ import annotations

from src.messages.sanitize.verbalize import (
    verbalize_email,
    verbalize_emails,
    verbalize_phone_digit,
    verbalize_phone_number,
    verbalize_phone_numbers,
)

# --- verbalize_email ---


def test_verbalize_email_basic() -> None:
    assert verbalize_email("me@you.com") == "me at you dot com"


# --- verbalize_emails ---


def test_verbalize_emails_empty() -> None:
    assert verbalize_emails("") == ""


def test_verbalize_emails_inline() -> None:
    result = verbalize_emails("reach me@you.com or them@here.org")
    assert "me at you dot com" in result
    assert "them at here dot org" in result


# --- verbalize_phone_digit ---


def test_verbalize_phone_digit_plus() -> None:
    assert verbalize_phone_digit("+") == "plus"


def test_verbalize_phone_digit_number() -> None:
    assert verbalize_phone_digit("1") == "one"
    assert verbalize_phone_digit("0") == "zero"
    assert verbalize_phone_digit("9") == "nine"


def test_verbalize_phone_digit_non_digit() -> None:
    assert verbalize_phone_digit(" ") == ""
    assert verbalize_phone_digit("-") == ""


# --- verbalize_phone_number ---


def test_verbalize_phone_number_basic() -> None:
    result = verbalize_phone_number("+1 234")
    assert "plus" in result
    assert "one" in result
    assert "two" in result
    assert "three" in result
    assert "four" in result


# --- verbalize_phone_numbers ---


def test_verbalize_phone_numbers_empty() -> None:
    assert verbalize_phone_numbers("") == ""


def test_verbalize_phone_numbers_no_numbers() -> None:
    assert verbalize_phone_numbers("no numbers") == "no numbers"


def test_verbalize_phone_numbers_international() -> None:
    result = verbalize_phone_numbers("call +1 234 567 8900 now")
    assert "+" not in result or "plus" in result
    # The original phone number should be replaced
    assert "234 567 8900" not in result
