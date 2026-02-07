"""Time-related dataclasses."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SessionTimestamp:
    """Structured representation of a session timestamp."""

    iso: str
    classification: str
    display: str
    tz: str


__all__ = ["SessionTimestamp"]
