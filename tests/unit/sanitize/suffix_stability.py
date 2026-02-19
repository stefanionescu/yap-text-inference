"""Unit tests for streaming suffix stability detectors."""

from __future__ import annotations

from src.messages.sanitize.suffix import (
    email_suffix_len,
    phone_suffix_len,
    emoticon_suffix_len,
    html_tag_suffix_len,
    unstable_suffix_len,
    html_entity_suffix_len,
    compute_stable_and_tail_lengths,
)

# --- unstable_suffix_len ---


def test_unstable_suffix_trailing_spaces() -> None:
    assert unstable_suffix_len("hello   ") > 0


def test_unstable_suffix_trailing_tabs() -> None:
    assert unstable_suffix_len("hello\t\t") > 0


def test_unstable_suffix_trailing_dots() -> None:
    assert unstable_suffix_len("hello...") == 3


def test_unstable_suffix_no_suffix() -> None:
    assert unstable_suffix_len("hello") == 0


# --- html_entity_suffix_len ---


def test_html_entity_partial_amp() -> None:
    assert html_entity_suffix_len("text &amp") > 0


def test_html_entity_complete_entity() -> None:
    assert html_entity_suffix_len("text &amp;") == 0


def test_html_entity_no_ampersand() -> None:
    assert html_entity_suffix_len("plain text") == 0


# --- html_tag_suffix_len ---


def test_html_tag_unclosed() -> None:
    assert html_tag_suffix_len("text <div") > 0


def test_html_tag_closed() -> None:
    assert html_tag_suffix_len("text <div>") == 0


def test_html_tag_heart_emoticon() -> None:
    assert html_tag_suffix_len("I <3 you") == 0


def test_html_tag_empty() -> None:
    assert html_tag_suffix_len("") == 0


# --- email_suffix_len ---


def test_email_full_email_present() -> None:
    result = email_suffix_len("contact me@you.com")
    assert result > 0


def test_email_partial_at_domain() -> None:
    result = email_suffix_len("contact user@domain")
    assert result > 0


def test_email_no_match() -> None:
    assert email_suffix_len("no email here!") == 0


def test_email_empty() -> None:
    assert email_suffix_len("") == 0


# --- phone_suffix_len ---


def test_phone_partial_digits() -> None:
    assert phone_suffix_len("call me +1 234") > 0


def test_phone_no_match() -> None:
    assert phone_suffix_len("no phone here!") == 0


def test_phone_empty() -> None:
    assert phone_suffix_len("") == 0


# --- emoticon_suffix_len ---


def test_emoticon_colon() -> None:
    assert emoticon_suffix_len("hello :") > 0


def test_emoticon_colon_dash() -> None:
    assert emoticon_suffix_len("hello :-") > 0


def test_emoticon_less_than() -> None:
    assert emoticon_suffix_len("I love you <") > 0


def test_emoticon_x_potential_xd() -> None:
    assert emoticon_suffix_len("haha X") > 0


def test_emoticon_caret_underscore() -> None:
    assert emoticon_suffix_len("yay ^_") > 0


def test_emoticon_empty() -> None:
    assert emoticon_suffix_len("") == 0


# --- compute_stable_and_tail_lengths ---


def test_compute_empty_sanitized() -> None:
    stable, tail = compute_stable_and_tail_lengths("", "", max_tail=64)
    assert stable == 0
    assert tail == 0


def test_compute_all_guards_zero() -> None:
    # Use a string ending in punctuation so no suffix detector triggers
    stable, tail = compute_stable_and_tail_lengths("ok!", "ok!", max_tail=64)
    assert stable == 3
    assert tail == 0


def test_compute_max_tail_capping() -> None:
    # Create a string with a long trailing unstable suffix
    text = "x" + " " * 100
    stable, tail = compute_stable_and_tail_lengths(text, text, max_tail=10)
    assert tail <= 10
    assert stable + tail == len(text)
