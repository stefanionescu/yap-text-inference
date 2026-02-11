"""Streaming sanitizer test.

Tests that the StreamingSanitizer produces the same output whether text is
streamed in chunks or processed in a single pass.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

import pytest

from tests.helpers.setup import setup_repo_path
from tests.messages import STREAMING_SANITIZER_CASES


def _ensure_test_env() -> None:
    """Set required env vars before importing src modules."""
    setup_repo_path()
    os.environ.setdefault("DEPLOY_MODE", "none")
    os.environ.setdefault("MAX_CONCURRENT_CONNECTIONS", "1")
    os.environ.setdefault("TEXT_API_KEY", "test")


_ensure_test_env()

from src.messages.sanitize.stream import StreamingSanitizer, _sanitize_stream_chunk  # noqa: E402


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


def _sanitize_once(text: str) -> str:
    sanitized, _, _ = _sanitize_stream_chunk(text, prefix_pending=True, capital_pending=True, strip_leading_ws=True)
    return sanitized.rstrip()


@pytest.mark.parametrize("text,splits", STREAMING_SANITIZER_CASES)
def test_streaming_matches_single_pass(text: str, splits: list[int]):
    streamed = _stream_chunks(text, splits)
    expected = _sanitize_once(text)
    if streamed != expected:
        raise AssertionError(f"sanitizer mismatch: {streamed!r} != {expected!r}")
