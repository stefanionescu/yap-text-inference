"""Base error classes shared by test helpers."""

from __future__ import annotations


class TestClientError(Exception):
    """Base class for all test client errors."""


__all__ = ["TestClientError"]
