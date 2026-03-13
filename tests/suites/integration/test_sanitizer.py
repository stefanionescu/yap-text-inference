"""Integration coverage for streaming sanitizer correctness and chunk stability."""

from __future__ import annotations

import os
import pytest
from collections.abc import Sequence
from tests.support.helpers.setup import setup_repo_path
from tests.support.messages import STREAMING_SANITIZER_CASES


def _ensure_test_env() -> None:
    """Set required env vars before importing src modules."""
    setup_repo_path()
    os.environ.setdefault("DEPLOY_MODE", "none")
    os.environ.setdefault("MAX_CONCURRENT_CONNECTIONS", "1")
    os.environ.setdefault("TEXT_API_KEY", "test")


_ensure_test_env()

from src.messages.sanitize.stream import StreamingSanitizer  # noqa: E402


def _stream_chunks(text: str, splits: Sequence[int]) -> str:
    sanitizer = StreamingSanitizer()
    out: list[str] = []
    start = 0
    boundaries = list(splits)
    if not boundaries or boundaries[-1] != len(text):
        boundaries.append(len(text))
    for end in boundaries:
        out.append(sanitizer.push(text[start:end]))
        start = end
    out.append(sanitizer.flush())
    return "".join(out)


@pytest.mark.parametrize(
    ("text", "splits", "expected"),
    [
        ("HTML <b>bold</b> text", [], "HTML bold text"),
        ("Contact me at foo.bar@example.com now.", [], "Contact me at foo dot bar at example dot com now."),
        (
            "Call +1 415-555-1234 tomorrow.",
            [],
            "Call plus one four one five five five five one two three four tomorrow.",
        ),
        ("Freestyle mode. hello there", [15], "Hello there"),
        ("Hi 😊 there", [], "Hi there"),
        ("Dots . . . spaced out", [], "Dots . spaced out"),
        ("dash-separated-words", [], "Dash separated words"),
        (
            "Replay risk: Mark Mark Mark but no duplicates please.",
            [10, 20, 30, 40],
            "Replay risk: Mark Mark Mark but no duplicates please.",
        ),
        (
            "Mixed newline tokens /n and \\n and real newlines\nshould normalize.",
            [12, 30],
            "Mixed newline tokens and and real newlines should normalize.",
        ),
        (
            'Quotes and escaped \\"marks\\" stay safe.',
            [10, 20],
            "Quotes and escaped marks stay safe.",
        ),
    ],
)
def test_streaming_sanitizer_matches_literal_expected_output(
    text: str,
    splits: list[int],
    expected: str,
) -> None:
    assert _stream_chunks(text, splits) == expected


@pytest.mark.parametrize("text,splits", STREAMING_SANITIZER_CASES)
def test_streaming_sanitizer_is_chunk_boundary_stable(text: str, splits: list[int]) -> None:
    streamed = _stream_chunks(text, splits)
    single_chunk = _stream_chunks(text, [])
    assert streamed == single_chunk
